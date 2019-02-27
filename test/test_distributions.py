from functools import reduce
from operator import mul

import jax.numpy as np
import jax.random as random
import numpy as onp
import pytest
import scipy.stats as sp
from jax import lax, grad

import numpyro.distributions as dist
from numpyro.distributions.util import standard_gamma


@pytest.mark.parametrize('loc, scale', [
    (1, 1),
    (1., np.array([1., 2.])),
])
@pytest.mark.parametrize('prepend_shape', [
    None,
    (),
    (2,),
    (2, 3),
])
def test_shape(loc, scale, prepend_shape):
    rng = random.PRNGKey(0)
    expected_shape = lax.broadcast_shapes(*[np.shape(loc), np.shape(scale)])
    assert np.shape(dist.norm.rvs(loc, scale, random_state=rng)) == expected_shape
    assert np.shape(dist.norm(loc, scale).rvs(random_state=rng)) == expected_shape
    if prepend_shape is not None:
        expected_shape = prepend_shape + lax.broadcast_shapes(*[np.shape(loc), np.shape(scale)])
        assert np.shape(dist.norm.rvs(loc, scale, random_state=rng, size=expected_shape)) == expected_shape
        assert np.shape(dist.norm(loc, scale).rvs(random_state=rng, size=expected_shape)) == expected_shape


@pytest.mark.parametrize('loc, scale', [
    (1., 1.),
    (1., np.array([1., 2.])),
])
def test_sample_gradient(loc, scale):
    rng = random.PRNGKey(0)
    expected_shape = lax.broadcast_shapes(*[np.shape(loc), np.shape(scale)])

    def fn(loc, scale):
        return dist.norm.rvs(loc, scale, random_state=rng).sum()

    assert grad(fn)(loc, scale) == loc * reduce(mul, expected_shape[:len(expected_shape) - len(np.shape(loc))], 1.)
    assert onp.allclose(grad(fn, 1)(loc, scale), random.normal(rng, shape=expected_shape))


@pytest.mark.parametrize("loc_scale", [
    (),
    (1,),
    (1, 1),
    (1., np.array([1., 2.])),
])
def test_normal_logprob(loc_scale):
    rng = random.PRNGKey(2)
    samples = dist.norm.rvs(*loc_scale, random_state=rng)
    assert np.allclose(dist.norm.logpdf(samples, *loc_scale), sp.norm.logpdf(samples, *loc_scale))


@pytest.mark.parametrize('alpha, shape', [
    (1., ()),
    (1., (2,)),
    (np.array([1., 2.]), ()),
    (np.array([1., 2.]), (3, 2)),
])
def test_standard_gamma_shape(alpha, shape):
    rng = random.PRNGKey(0)
    expected_shape = lax.broadcast_shapes(np.shape(alpha), shape)
    assert np.shape(standard_gamma(rng, alpha, shape=shape)) == expected_shape


@pytest.mark.parametrize("alpha", [0.6, 2., 10.])
def test_standard_gamma_stats(alpha):
    rng = random.PRNGKey(0)
    z = standard_gamma(rng, np.full((1000,), alpha))
    assert np.abs((np.mean(z) - alpha) / alpha) < 0.06
    assert np.abs((np.var(z) - alpha) / alpha) < 0.2


@pytest.mark.parametrize("alpha", [1e-4, 1e-3, 1e-2, 1e-1, 1e0, 1e1, 1e2, 1e3, 1e4])
def test_standard_gamma_grad(alpha):
    rng = random.PRNGKey(0)
    alphas = np.full((100,), alpha)
    z = standard_gamma(rng, alphas)
    actual_grad = grad(lambda x: np.sum(standard_gamma(rng, x)))(alphas)

    eps = 0.01 * alpha / (1.0 + np.sqrt(alpha))
    cdf_dot = (sp.gamma.cdf(z, alpha + eps) - sp.gamma.cdf(z, alpha - eps)) / (2 * eps)
    pdf = sp.gamma.pdf(z, alpha)
    expected_grad = -cdf_dot / pdf

    error = np.abs((actual_grad - expected_grad) / expected_grad)
    assert np.max(error) < 0.0005
