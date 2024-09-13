#!/usr/bin/env python
# -*- coding: utf-8 -*-

# You can run this code outside of the Ray cluster!
import ray

# Starting the Ray client. This connects to a remote Ray cluster.
#  ray.init(_node_ip_address='192.168.88.197')
ray.init('ray://192.168.88.197:10002')


# Normal Ray code follows
@ray.remote
def do_work(x):
    return x ** x


@ray.remote
def fit_model():
    import arviz as az
    import matplotlib.pyplot as plt
    from lifetimes.datasets import load_cdnow_summary

    from pymc_marketing import clv

    az.style.use("arviz-darkgrid")
    plt.rcParams["figure.figsize"] = [12, 7]
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["figure.facecolor"] = "white"

    df = (
        load_cdnow_summary(index_col=[0])
        .reset_index()
        .rename(columns={"ID": "customer_id"})
    )
    sampler_kwargs = {
        "draws": 2_000,
        "target_accept": 0.9,
        "chains": 5,
        "random_seed": 42,
    }

    model = clv.BetaGeoModel(data=df)
    idata_nutpie = model.fit(nuts_sampler="nutpie", **sampler_kwargs)
    return idata_nutpie

object_ref = fit_model.remote()
x = ray.get(object_ref)
print(x)

"""
object_refs = do_work.remote(2)
x = ray.get(object_refs)
"""


