ARG NETBOX_BASE_IMAGE
FROM ${NETBOX_BASE_IMAGE}

USER root
COPY plugins/netbox_cots-0.2.0-py3-none-any.whl /opt/netbox/plugins/
RUN /usr/local/bin/uv pip install --python /opt/netbox/venv/bin/python \
    /opt/netbox/plugins/netbox_cots-0.2.0-py3-none-any.whl

USER netbox
