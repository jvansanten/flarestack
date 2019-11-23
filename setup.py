import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="flarestack",
    version="2.0.0-beta",
    author="Robert Stein",
    author_email="robert.stein@desy.de",
    description="Package for unbinned likelihood analysis of physics data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="astroparticle physics science unbinned likelihood IceCube",
    url="https://github.com/IceCubeOpenSource/flarestack",
    packages=setuptools.find_packages(),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires='>=3.6',
    install_requires=[
        "numpy",
        "numexpr",
        "healpy",
        "scipy",
        "matplotlib",
        "astropy",
        "sphinx",
        "jupyter",
        "python-coveralls"
    ],
    package_data={'flarestack': [
        'data/icecube/public/all_sky_point_source/raw_data/*.zip']},
    include_package_data=True
)

