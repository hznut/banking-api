from setuptools import setup, find_packages

setup(
    name="banking-api",
    version="0.1.0",
    description="Banking API",
    # url="https://github.td.teradata.com/VantageOnGCP/vgcp.git",
    author="Himanshu Vijay",
    author_email="himanshuvj@gmail.com",
    license="MIT",
    include_package_data=True,
    # install_requires=requirements,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
    ],
)