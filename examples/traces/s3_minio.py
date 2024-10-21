import s3fs
import xarray as xr
import arviz

# Configure the S3 connection (MinIO)
s3 = s3fs.S3FileSystem(
    anon=False,  # Set to True if your bucket allows anonymous access
    key='minioadmin',   # Replace with your MinIO access key
    secret='minioadmin', # Replace with your MinIO secret key
    client_kwargs={'endpoint_url': 'http://34.66.59.65:50002'}  # Replace with your MinIO URL
)

# Specify the path to the Zarr dataset in the MinIO bucket
zarr_path = 'upload/out.zarr'

# Open the Zarr dataset with xarray
store = s3fs.S3Map(root=zarr_path, s3=s3)
#ds = xr.open_zarr(store, consolidated=True)
ds = arviz.from_zarr(store)
print(ds)
breakpoint()

