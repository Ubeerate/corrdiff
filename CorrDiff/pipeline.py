import os
os.environ["HOME"] = os.environ.get("USERPROFILE", "")

import xarray as xr
import numpy as np
from scipy.interpolate import griddata
import argparse
from typing import Optional


class ModelWrapper:
    """Abstracts a model so weights can be swapped later.

    For now the wrapper uses an interpolation-based downscaler as a stub.
    Replace `load_weights` and `predict` to integrate the real CorrDiff model.
    """

    def __init__(self):
        self.weights_path: Optional[str] = None

    def load_weights(self, path: str):
        """Placeholder for loading model weights (CorrDiff package or files).

        When you have a CorrDiff package, call something like:
            pkg = Package(root)
            model = CorrDiff.load_model(pkg, device='cuda:0')
            self._model = model
        """
        self.weights_path = path

    def predict(self, ds: xr.Dataset, sr_factor: int = 2) -> xr.Dataset:
        """Run model inference.

        Current implementation: cubic interpolation upscale (placeholder).
        """
        # If a real model were present, call it here. For now use interpolation.
        return downscale_by_interpolation(ds, sr_factor=sr_factor)


def load_input(path: str) -> xr.Dataset:
    """Load an input NetCDF file as an xarray Dataset."""
    ds = xr.open_dataset(path)
    return ds


def downscale_by_interpolation(ds: xr.Dataset, sr_factor: int = 2) -> xr.Dataset:
    """Simple spatial upscaling using griddata (cubic).

    Supports datasets where `u10`/`v10` have either (time, lat, lon) or
    (lat, lon) shapes. Returns an xr.Dataset with upscaled `u10` and `v10`.
    """
    # pick arrays (remove time if present)
    if ds['u10'].ndim == 3:
        u = ds['u10'][0].values
        v = ds['v10'][0].values
    else:
        u = ds['u10'].values
        v = ds['v10'].values

    lat = ds['latitude'].values
    lon = ds['longitude'].values

    # Build high-resolution grids
    sr_lat = np.linspace(lat.min(), lat.max(), len(lat) * sr_factor - (sr_factor - 1))
    sr_lon = np.linspace(lon.min(), lon.max(), len(lon) * sr_factor - (sr_factor - 1))
    sr_lat_grid, sr_lon_grid = np.meshgrid(sr_lat, sr_lon, indexing='ij')

    lat_grid, lon_grid = np.meshgrid(lat, lon, indexing='ij')

    points = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
    u_sr = griddata(points, u.ravel(), (sr_lat_grid, sr_lon_grid), method='cubic')
    v_sr = griddata(points, v.ravel(), (sr_lat_grid, sr_lon_grid), method='cubic')

    out_ds = xr.Dataset(
        {
            'u10': (['latitude', 'longitude'], u_sr.astype(np.float32)),
            'v10': (['latitude', 'longitude'], v_sr.astype(np.float32)),
        },
        coords={
            'latitude': sr_lat,
            'longitude': sr_lon,
        }
    )

    # compute wind speed
    ws = np.sqrt(u_sr**2 + v_sr**2)
    out_ds['wind_speed'] = (['latitude', 'longitude'], ws.astype(np.float32))

    return out_ds


def save_output(ds: xr.Dataset, path: str):
    """Save Dataset to NetCDF4 file with recommended options."""
    ds.to_netcdf(path, format='NETCDF4')


def run_pipeline(input_path: str, output_path: str, sr_factor: int = 2, weights: Optional[str] = None):
    """Full pipeline: load -> model.predict (interpolation stub) -> save."""
    print(f"📖 Loading input: {input_path}")
    ds = load_input(input_path)
    print(f"ℹ️ Found dimensions: {dict(ds.dims)}")

    model = ModelWrapper()
    if weights:
        print(f"🔁 Loading model weights from: {weights} (placeholder)")
        model.load_weights(weights)

    print(f"🔄 Running downscale (sr_factor={sr_factor}) using interpolation stub...")
    out_ds = model.predict(ds, sr_factor=sr_factor)

    print(f"💾 Saving output to: {output_path}")
    save_output(out_ds, output_path)
    print("✅ Pipeline complete.")


def cli():
    parser = argparse.ArgumentParser(description='CorrDiff compatible pipeline (stubbed interpolation)')
    parser.add_argument('--input', '-i', required=True, help='Input NetCDF file (coarse resolution)')
    parser.add_argument('--output', '-o', required=True, help='Output NetCDF file (upscaled)')
    parser.add_argument('--sr-factor', type=int, default=2, choices=[1,2,3,4], help='Super-resolution factor')
    parser.add_argument('--weights', type=str, default=None, help='Path to model weights or package (placeholder)')
    args = parser.parse_args()

    run_pipeline(args.input, args.output, sr_factor=args.sr_factor, weights=args.weights)


if __name__ == '__main__':
    cli()
