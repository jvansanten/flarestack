import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from shared import illustration_dir
import scipy.stats

plt.xkcd()

n_zero = 10000

standard_path = illustration_dir + "ts_standard_hist.png"

delta = np.zeros(n_zero)

chi2 = scipy.stats.chi2.rvs(df=1.4, loc=0, scale=1, size=5000)

data = list(chi2) + list(delta)
weight = np.ones_like(data)/float(len(data))

plt.figure()
plt.hist(data, weights=weight, bins=50)
plt.axvline(np.median(data), color="red", linestyle="--")
plt.xlabel("TS")
plt.yscale("log")
plt.savefig(standard_path)
plt.close()

unbound_path = illustration_dir + "ts_negative_hist.png"

negative = -scipy.stats.chi2.rvs(df=3.0, loc=0, scale=1, size=n_zero)

data = list(chi2) + list(negative)
weight = np.ones_like(data)/float(len(data))

plt.figure()
plt.hist(data, weights=weight, bins=50)
plt.axvline(np.median(data), color="red", linestyle="--")
plt.xlabel("TS")
plt.yscale("log")
plt.savefig(unbound_path)
plt.close()

standard_llh_path = illustration_dir + "llh_standard.png"

x = np.linspace(0, 50, 500)

cut = -7.


def y(x):
    return (x+5.)**2 + 1./(x - cut)**0.5


def f(x):
    return y(x) - y(0)


plt.figure()
plt.plot(x, f(x))
plt.scatter(0., 0., color="r", marker="*", s=100, zorder=3)
plt.ylabel(r"$\Delta$ LLH")
plt.xlabel(r"$n_{s}$")
plt.savefig(standard_llh_path)
plt.close()

unbound_llh_path = illustration_dir + "llh_unbound.png"

x = np.linspace(cut + 0.01, 10, 500)

plt.figure()
plt.plot(x, f(x), zorder=1)
best_index = list(f(x)).index(min(f(x)))
plt.scatter(x[best_index], min(f(x)), color="r", marker="*", s=100, zorder=3)
plt.axvline(cut, color="b", linestyle="--", zorder=2)
plt.ylabel(r"$\Delta$ LLH")
plt.xlabel(r"$n_{s}$")
plt.savefig(unbound_llh_path)
plt.close()






