import os
import argparse
import xarray as xr
import numpy as np
import matplotlib
# Use non-interactive Agg backend to avoid GUI/Qt issues when saving figures
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from PIL import Image
from PIL import ImageDraw
from scipy.interpolate import RegularGridInterpolator

# Optional cartopy
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    CARTOPY_AVAILABLE = True
except Exception:
    CARTOPY_AVAILABLE = False

if CARTOPY_AVAILABLE:
    try:
        from cartopy.io import shapereader
    except Exception:
        shapereader = None
else:
    shapereader = None

# NOTE: some Windows / Cartopy builds trigger C-level faults in some envs.
# We keep CARTOPY_AVAILABLE set by the import check above. Use the
# `--use-cartopy` flag to enable Cartopy plotting; the code will test and
# fall back to the safe PIL output if Cartopy fails at runtime.


# Default time value (edit this string to quickly switch plot time)
# Examples: "2020-06-25" or "2020-06-25T00:00"
TIME_VALUE_DEFAULT = "2020-06-25"


class SuperResolutionWind:
    """Super-resolution helper for u10/v10 wind fields on a regular lat/lon grid."""

    def __init__(self, input_file, sr_factor=2, time_index=0, time_value=None):
        self.input_file = input_file
        self.sr_factor = int(sr_factor)
        self.time_index = int(time_index)
        self.time_value = time_value
        self.ds = None
        self.sr_ds = None
        self.has_time = False
        self.time_dim = None
        self.load_data()

    def load_data(self):
        print(f"📖 Loading {self.input_file}...")
        self.ds = xr.open_dataset(self.input_file)
        # Expect variables `u10` and `v10` and coords `latitude`, `longitude`
        if self.ds['u10'].ndim == 3:
            self.has_time = True
            time_dim = self.ds['u10'].dims[0]
            self.time_dim = time_dim
            try:
                ntime = len(self.ds[time_dim])
            except Exception:
                ntime = self.ds['u10'].shape[0]
            print(f"✅ Original resolution: {len(self.ds.latitude)} × {len(self.ds.longitude)} (time: {ntime})")
            # If a time_value string was provided, resolve it to an index
            if self.time_value is not None:
                resolved = self._time_index_for_value(self.time_value)
                if resolved is not None:
                    self.time_index = int(resolved)
                    print(f"🔧 resolved time_value {self.time_value} -> time_index = {self.time_index}")
                else:
                    print(f"⚠️ could not resolve time_value {self.time_value}; using time_index = {self.time_index}")
            else:
                print(f"🔧 using time_index = {self.time_index}")
        else:
            self.has_time = False
            print(f"✅ Original resolution: {len(self.ds.latitude)} × {len(self.ds.longitude)}")

    def _time_index_for_value(self, time_value):
        """Resolve a user-supplied time_value (string or numeric) to the nearest index on the dataset time coordinate.
        Returns integer index or None if resolution failed."""
        if self.time_dim is None:
            return None
        times = self.ds[self.time_dim].values
        try:
            # datetimelike
            if np.issubdtype(times.dtype, np.datetime64):
                try:
                    target = np.datetime64(time_value)
                except Exception:
                    # try parsing with pandas if available
                    try:
                        import pandas as pd
                        target = np.datetime64(pd.to_datetime(time_value))
                    except Exception:
                        return None
                diffs = np.abs(times - target)
                idx = int(diffs.argmin())
                return idx
            # numeric times
            elif np.issubdtype(times.dtype, np.number):
                try:
                    val = float(time_value)
                except Exception:
                    return None
                diffs = np.abs(times - val)
                idx = int(diffs.argmin())
                return idx
            else:
                # fallback: string match
                str_times = np.array([str(t) for t in times])
                matches = np.where(str_times == str(time_value))[0]
                if len(matches) > 0:
                    return int(matches[0])
                return None
        except Exception:
            return None

    def super_resolve(self):
        """Create a higher-resolution dataset using interpolation."""
        print(f"\n🔄 Running {self.sr_factor}x super-resolution...")
        lat = self.ds.latitude.values
        lon = self.ds.longitude.values

        if self.has_time and self.ds['u10'].ndim == 3:
            u10 = self.ds.u10[self.time_index].values
            v10 = self.ds.v10[self.time_index].values
        else:
            u10 = self.ds.u10.values
            v10 = self.ds.v10.values

        # build sr grid (keep endpoints)
        sr_lat = np.linspace(lat.min(), lat.max(), len(lat) * self.sr_factor - (self.sr_factor - 1))
        sr_lon = np.linspace(lon.min(), lon.max(), len(lon) * self.sr_factor - (self.sr_factor - 1))
        sr_lat_grid, sr_lon_grid = np.meshgrid(sr_lat, sr_lon, indexing='ij')

        # Interpolate using RegularGridInterpolator (robust for regular grids)
        interp_u = RegularGridInterpolator((lat, lon), u10, bounds_error=False, fill_value=None)
        interp_v = RegularGridInterpolator((lat, lon), v10, bounds_error=False, fill_value=None)
        pts = np.column_stack([sr_lat_grid.ravel(), sr_lon_grid.ravel()])
        u10_sr = interp_u(pts).reshape(sr_lat_grid.shape)
        v10_sr = interp_v(pts).reshape(sr_lat_grid.shape)

        # Build xarray Dataset for SR fields
        self.sr_ds = xr.Dataset(
            {
                'u10': (['latitude', 'longitude'], u10_sr),
                'v10': (['latitude', 'longitude'], v10_sr),
            },
            coords={'latitude': sr_lat, 'longitude': sr_lon}
        )

        print(f"✅ New resolution: {len(sr_lat)} × {len(sr_lon)}")
        return self.sr_ds

    def get_wind_speed_and_direction(self, ds=None):
        if ds is None:
            ds = self.sr_ds if self.sr_ds is not None else self.ds
        if ds['u10'].ndim == 3:
            u10 = ds['u10'][self.time_index].values
            v10 = ds['v10'][self.time_index].values
        else:
            u10 = ds['u10'].values
            v10 = ds['v10'].values
        wind_speed = np.sqrt(u10 ** 2 + v10 ** 2)
        wind_direction = (np.degrees(np.arctan2(u10, v10)) % 360)
        return wind_speed, wind_direction, u10, v10

    def _overlay_coastlines_on_array(self, img_arr, lon_vals, lat_vals, line_color=(0,0,0,255), width=1):
        """Draw coastlines from Natural Earth onto an RGBA numpy array and return a PIL Image."""
        if shapereader is None:
            return Image.fromarray(img_arr)
        img = Image.fromarray(img_arr).convert('RGBA')
        draw = ImageDraw.Draw(img)
        lon_min, lon_max = float(lon_vals.min()), float(lon_vals.max())
        lat_min, lat_max = float(lat_vals.min()), float(lat_vals.max())
        H, W = img_arr.shape[0], img_arr.shape[1]

        def proj_xy(lon, lat):
            x = (lon - lon_min) / (lon_max - lon_min) * (W - 1)
            y = (lat - lat_min) / (lat_max - lat_min) * (H - 1)
            return (x, H - 1 - y)

        try:
            shp = shapereader.natural_earth(resolution='10m', category='physical', name='coastline')
            reader = shapereader.Reader(shp)
            for geom in reader.geometries():
                try:
                    coords = list(geom.coords)
                    pts = [proj_xy(lon, lat) for lon, lat in coords]
                    draw.line(pts, fill=line_color, width=width)
                except Exception:
                    for part in geom:
                        try:
                            coords = list(part.coords)
                            pts = [proj_xy(lon, lat) for lon, lat in coords]
                            draw.line(pts, fill=line_color, width=width)
                        except Exception:
                            continue
        except Exception:
            return Image.fromarray(img_arr)
        return img

    def plot_wind_detail(self, output_file, use_cartopy=False, coastline_overlay=False):
        if self.sr_ds is None:
            print('⚠️ Run super_resolve() first')
            return
        wind_speed, wind_direction, u10, v10 = self.get_wind_speed_and_direction()

        # Try Cartopy rendering if requested and available
        if use_cartopy and CARTOPY_AVAILABLE:
            try:
                fig = plt.figure(figsize=(16, 12))
                axes = [fig.add_subplot(2, 2, i + 1, projection=ccrs.PlateCarree()) for i in range(4)]
                axes = np.array(axes).reshape(2, 2)

                ax = axes[0, 0]
                ax.contourf(self.sr_ds.longitude.values, self.sr_ds.latitude.values, wind_speed, levels=20, cmap='RdYlBu_r', transform=ccrs.PlateCarree())
                ax.contour(self.sr_ds.longitude.values, self.sr_ds.latitude.values, wind_speed, levels=10, colors='k', alpha=0.3, linewidths=0.5, transform=ccrs.PlateCarree())
                skip = max(1, self.sr_factor)
                ax.coastlines(resolution='10m')
                ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
                ax.quiver(self.sr_ds.longitude.values[::skip], self.sr_ds.latitude.values[::skip], u10[::skip, ::skip], v10[::skip, ::skip], transform=ccrs.PlateCarree())
                ax.set_title('Wind speed + vectors')

                ax = axes[0, 1]
                ax.contourf(self.sr_ds.longitude.values, self.sr_ds.latitude.values, u10, levels=20, cmap='RdBu_r', transform=ccrs.PlateCarree())
                ax.coastlines(resolution='10m'); ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
                ax.set_title('U component')

                ax = axes[1, 0]
                ax.contourf(self.sr_ds.longitude.values, self.sr_ds.latitude.values, v10, levels=20, cmap='RdBu_r', transform=ccrs.PlateCarree())
                ax.coastlines(resolution='10m'); ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
                ax.set_title('V component')

                ax = axes[1, 1]
                ax.contourf(self.sr_ds.longitude.values, self.sr_ds.latitude.values, wind_direction, levels=16, cmap=plt.cm.hsv, vmin=0, vmax=360, transform=ccrs.PlateCarree())
                ax.coastlines(resolution='10m'); ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
                ax.set_title('Wind direction (deg)')

                plt.savefig(output_file, dpi=150, bbox_inches='tight')
                print(f"✅ Saved (Cartopy): {output_file}")
                plt.close()
                return
            except Exception as e:
                print('⚠️ Cartopy rendering failed; falling back to safe PIL output')

        # Fallback: render images via PIL+colormap (safe)
        def to_rgba(arr, cmap_name='RdYlBu_r'):
            cmap = plt.get_cmap(cmap_name)
            a = np.array(arr, dtype=float)
            vmin = np.nanmin(a)
            vmax = np.nanmax(a)
            if vmax == vmin:
                vmax = vmin + 1e-6
            normed = (a - vmin) / (vmax - vmin)
            rgba = cmap(normed)
            rgba8 = (rgba * 255).astype(np.uint8)
            return rgba8

        img1 = to_rgba(wind_speed, 'RdYlBu_r')
        img2 = to_rgba(u10, 'RdBu_r')
        img3 = to_rgba(v10, 'RdBu_r')
        img4 = to_rgba(wind_direction, 'hsv')

        h, w, _ = img1.shape

        def overlay_coastlines_on_array(img_arr, lon_vals, lat_vals, line_color=(0,0,0,255), width=1):
            if shapereader is None:
                return Image.fromarray(img_arr)
            img = Image.fromarray(img_arr).convert('RGBA')
            draw = ImageDraw.Draw(img)
            lon_min, lon_max = float(lon_vals.min()), float(lon_vals.max())
            lat_min, lat_max = float(lat_vals.min()), float(lat_vals.max())
            H, W = img_arr.shape[0], img_arr.shape[1]

            def proj_xy(lon, lat):
                x = (lon - lon_min) / (lon_max - lon_min) * (W - 1)
                y = (lat - lat_min) / (lat_max - lat_min) * (H - 1)
                return (x, H - 1 - y)

            try:
                shp = shapereader.natural_earth(resolution='10m', category='physical', name='coastline')
                reader = shapereader.Reader(shp)
                for geom in reader.geometries():
                    # geom may be LineString or MultiLineString
                    try:
                        coords = list(geom.coords)
                        pts = [proj_xy(lon, lat) for lon, lat in coords]
                        draw.line(pts, fill=line_color, width=width)
                    except Exception:
                        # handle multipart
                        for part in geom:
                            try:
                                coords = list(part.coords)
                                pts = [proj_xy(lon, lat) for lon, lat in coords]
                                draw.line(pts, fill=line_color, width=width)
                            except Exception:
                                continue
            except Exception:
                return Image.fromarray(img_arr)
            return img

        mosaic = Image.new('RGBA', (w * 2, h * 2))
        panel1 = self._overlay_coastlines_on_array(img1, self.sr_ds.longitude.values, self.sr_ds.latitude.values) if coastline_overlay else Image.fromarray(img1)
        panel2 = self._overlay_coastlines_on_array(img2, self.sr_ds.longitude.values, self.sr_ds.latitude.values) if coastline_overlay else Image.fromarray(img2)
        panel3 = self._overlay_coastlines_on_array(img3, self.sr_ds.longitude.values, self.sr_ds.latitude.values) if coastline_overlay else Image.fromarray(img3)
        panel4 = self._overlay_coastlines_on_array(img4, self.sr_ds.longitude.values, self.sr_ds.latitude.values) if coastline_overlay else Image.fromarray(img4)
        mosaic.paste(panel1, (0, 0))
        mosaic.paste(panel2, (w, 0))
        mosaic.paste(panel3, (0, h))
        mosaic.paste(panel4, (w, h))
        mosaic.save(output_file)
        print(f"✅ Saved (PIL): {output_file}")

    def plot_comparison(self, output_file, use_cartopy=False, coastline_overlay=False):
        if self.sr_ds is None:
            print('⚠️ Run super_resolve() first')
            return
        if self.ds['u10'].ndim == 3:
            u10_orig = self.ds['u10'][self.time_index].values
            v10_orig = self.ds['v10'][self.time_index].values
        else:
            u10_orig = self.ds['u10'].values
            v10_orig = self.ds['v10'].values
        wind_orig = np.sqrt(u10_orig ** 2 + v10_orig ** 2)
        wind_sr, _, u10_sr, v10_sr = self.get_wind_speed_and_direction()

        # Try Cartopy comparison if requested
        if use_cartopy and CARTOPY_AVAILABLE:
            try:
                fig = plt.figure(figsize=(14, 5))
                ax1 = fig.add_subplot(1, 2, 1, projection=ccrs.PlateCarree())
                ax2 = fig.add_subplot(1, 2, 2, projection=ccrs.PlateCarree())

                ax1.contourf(self.ds.longitude.values, self.ds.latitude.values, wind_orig, levels=20, cmap='RdYlBu_r', transform=ccrs.PlateCarree())
                ax1.coastlines(resolution='10m'); ax1.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
                ax1.set_title('Original')

                ax2.contourf(self.sr_ds.longitude.values, self.sr_ds.latitude.values, wind_sr, levels=20, cmap='RdYlBu_r', transform=ccrs.PlateCarree())
                ax2.coastlines(resolution='10m'); ax2.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
                ax2.set_title(f'SR {self.sr_factor}x')

                plt.savefig(output_file, dpi=150, bbox_inches='tight')
                print(f"✅ Saved (Cartopy): {output_file}")
                plt.close()
                return
            except Exception:
                print('⚠️ Cartopy comparison failed; falling back to safe PIL output')

        def to_rgba(arr, cmap_name='RdYlBu_r'):
            cmap = plt.get_cmap(cmap_name)
            a = np.array(arr, dtype=float)
            vmin = np.nanmin(a)
            vmax = np.nanmax(a)
            if vmax == vmin:
                vmax = vmin + 1e-6
            normed = (a - vmin) / (vmax - vmin)
            rgba = cmap(normed)
            rgba8 = (rgba * 255).astype(np.uint8)
            return rgba8

        img1 = to_rgba(wind_orig)
        img2 = to_rgba(wind_sr)
        h, w, _ = img1.shape
        if coastline_overlay:
            panel1 = self._overlay_coastlines_on_array(img1, self.ds.longitude.values, self.ds.latitude.values)
            panel2 = self._overlay_coastlines_on_array(img2, self.sr_ds.longitude.values, self.sr_ds.latitude.values)
        else:
            panel1 = Image.fromarray(img1)
            panel2 = Image.fromarray(img2)
        mosaic = Image.new('RGBA', (w * 2, h))
        mosaic.paste(panel1, (0, 0))
        mosaic.paste(panel2, (w, 0))
        mosaic.save(output_file)
        print(f"✅ Saved (PIL): {output_file}")
        plt.close()

    def print_statistics(self):
        wind_speed, wind_direction, u10, v10 = self.get_wind_speed_and_direction()
        print('\n' + '=' * 40)
        print('Wind statistics')
        print(f"max: {wind_speed.max():.2f} m/s, mean: {wind_speed.mean():.2f} m/s")
        print('=' * 40)


def main():
    parser = argparse.ArgumentParser(description='Super-resolution wind tool')
    parser.add_argument('--sr-factor', type=int, default=2, choices=[1, 2, 3, 4])
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--use-cartopy', action='store_true', help='Try to render with Cartopy (optional, may crash on some Windows envs)')
    parser.add_argument('--coastline-overlay', action='store_true', help='Overlay coastlines (uses Natural Earth via Cartopy shapereader)')
    parser.add_argument('--input', type=str, default='taiwan_test_data.nc')
    parser.add_argument('--time-index', type=int, default=0)
    parser.add_argument('--time-value', type=str, default=None, help='Time value (string or numeric) to resolve to a time index')
    parser.add_argument('--out-dir', type=str, default='CorrDiff/outputs')

    args = parser.parse_args()
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    # Determine time_value: prefer CLI --time-value, otherwise use TIME_VALUE_DEFAULT
    time_value_to_use = args.time_value if args.time_value is not None else TIME_VALUE_DEFAULT

    sr = SuperResolutionWind(input_file=args.input, sr_factor=args.sr_factor, time_index=args.time_index, time_value=time_value_to_use)
    sr.super_resolve()
    detail_path = os.path.join(out_dir, f'wind_detail_sr{args.sr_factor}x.png')
    sr.plot_wind_detail(detail_path, use_cartopy=args.use_cartopy, coastline_overlay=args.coastline_overlay)
    if args.compare:
        compare_path = os.path.join(out_dir, f'wind_comparison_{args.sr_factor}x.png')
        sr.plot_comparison(compare_path, use_cartopy=args.use_cartopy, coastline_overlay=args.coastline_overlay)
    sr.print_statistics()


if __name__ == '__main__':
    main()
