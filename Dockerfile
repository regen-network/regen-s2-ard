FROM ubuntu:18.04
LABEL MAINTAINER="Regen Network"

# SYSTEM
RUN apt-get update && \
    apt-get install -y curl file unzip && \
    mkdir /output /work /app && \
    chmod 777 /output /work /app

# SEN2COR
RUN curl -o /usr/local/etc/sen2cor.run http://step.esa.int/thirdparties/sen2cor/2.8.0/Sen2Cor-02.08.00-Linux64.run && \
    sh /usr/local/etc/sen2cor.run && \
    rm /usr/local/etc/sen2cor.run
ENV PATH=$PATH:/Sen2Cor-02.08.00-Linux64/bin

# INSTALL MINICONDA
RUN curl -LO http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash Miniconda3-latest-Linux-x86_64.sh -p /miniconda -b
RUN rm Miniconda3-latest-Linux-x86_64.sh
ENV PATH=/miniconda/bin:${PATH}

# CONDA INSTALL PACKAGES
RUN conda install python=3.7
RUN conda install -c conda-forge gdal=2.4.2
RUN conda install -c conda-forge python-fmask
RUN conda install -c conda-forge ruamel.yaml=0.15.96

ENV HOME=/app
WORKDIR $HOME
COPY src $HOME
