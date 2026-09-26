FROM python:3.12-slim
WORKDIR /app

# install uv
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

COPY pyproject.toml uv.lock ./

RUN uv sync

COPY . .

EXPOSE 8787

CMD ["uv", "run", "uvicorn", "main:app",  "--host",  "0.0.0.0", "--port", "8787", "--reload"]
