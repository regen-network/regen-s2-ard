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
RUN curl -LO http://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh
RUN bash Miniconda-latest-Linux-x86_64.sh -p /miniconda -b
RUN rm Miniconda-latest-Linux-x86_64.sh
ENV PATH=/miniconda/bin:${PATH}
RUN conda update -y conda

# CONDA INSTALL PACKAGES
RUN conda install -c conda-forge gdal=2.4.2
RUN conda install -c conda-forge python-fmask
RUN conda install -c conda-forge ruamel.yaml=0.15.96

# INSTALL GSUTIL
# Downloading gcloud package
RUN curl https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /usr/local/etc/google-cloud-sdk.tar.gz
# Installing the package
RUN mkdir -p /usr/local/gcloud && \
    tar -C /usr/local/gcloud -xvf /usr/local/etc/google-cloud-sdk.tar.gz && \
    /usr/local/gcloud/google-cloud-sdk/install.sh
# Adding the package path to local
ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin

ENV HOME=/app
WORKDIR $HOME
COPY src $HOME

#ENTRYPOINT ["python", "ard.py"]
