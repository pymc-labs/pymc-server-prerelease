from pymc_server.connectivity.connect_ray import(
    RemoteStatefulActorWrapper,
    Pong
)

from ray import remote
import ray
pymcs_namespace = 'dev_2'



@remote
class PymcTraceActor:
    """An example actor that can be used as the RemoteStatefulActorWrapper implementation attribute"""
    def __init__(self, foo='foo', bar='bar'):
        self.foo = foo
        self.bar = bar
        self.invocation_count = 0
        self.baz = 1
        self.result = None
        self.done = False
        self.is_ser = None

    def reset(self):
        self.invocation_count = 0

    def _foobar(self):
        print(super())
        self.invocation_count += 1
        self.baz=42
        #self.set_attribute('invocation_count', 100)
        return 'foobar'

    def _ping(self):
        return Pong()

    def get_attribute(self, attr_name):
        return getattr(self, attr_name)

    def set_attribute(self, attr_name, value):
        setattr(self, attr_name, value)

    def run(self):
        import pytensor
        import pytensor.tensor as pt
        import pymc as pm
        import numpy as np
        import nutpie
        import arviz
        import pandas as pd
        import matplotlib.pyplot as plt
        import zarr


        from pymc.model.transform.optimization import freeze_dims_and_data

        data = pd.read_csv(pm.get_data("radon.csv"))
        data["log_radon"] = data["log_radon"].astype(np.float64)
        county_idx, counties = pd.factorize(data.county)

        # Adding a couple larger vars, just to make the trace bigger
        # Just change those numbers to make the trace smaller or bigger
        coords = {
            "county": counties,
            "obs_id": np.arange(len(county_idx)),
            "large1": pd.RangeIndex(10),
            "large2": pd.RangeIndex(10),
            "large3": pd.RangeIndex(10),
        }

        # Define some random model
        with pm.Model(coords=coords, check_bounds=False) as model:
            intercept = pm.Normal("intercept", sigma=10)

            raw = pm.Normal("county_raw", dims="county")
            sd = pm.HalfNormal("county_sd")
            county_effect = pm.Deterministic("county_effect", raw * sd, dims="county")

            floor_effect = pm.Normal("floor_effect", sigma=2)

            raw = pm.Normal("county_floor_raw", dims="county")
            sd = pm.HalfNormal("county_floor_sd")
            county_floor_effect = pm.Deterministic(
                "county_floor_effect", raw * sd, dims="county"
            )

            mu = (
                intercept
                + county_effect[county_idx]
                + floor_effect * data.floor.values
                + county_floor_effect[county_idx] * data.floor.values
            )

            sigma = pm.HalfNormal("sigma", sigma=1.5)
            pm.Normal(
                "log_radon", mu=mu, sigma=sigma, observed=data.log_radon.values, dims="obs_id"
            )

            # Some useless vars just to make the trace bigger
            pm.Normal("large_var1", dims=("large1", "large2"))
            pm.Normal("large_var2", dims=("large2", "large3"))



        compiled = nutpie.compile_pymc_model(freeze_dims_and_data(model), backend="numba")

        # Sample using nutpie
        tr = nutpie.sample(compiled, store_unconstrained=True, store_gradient=True, seed=123)
        _ = tr.to_zarr("/tmp/output.zarr")
        self.result = tr
        from ray.util import inspect_serializability
        self.is_ser = inspect_serializability(tr, name="tr")

        self.done = True

server = RemoteStatefulActorWrapper(
    pymcs_namespace,
    implementation=PymcTraceActor,
    allow_local_fallback=False,
    foo='Pizza Hawaii',
    bar='911'
)

#print(server.run())

breakpoint()
