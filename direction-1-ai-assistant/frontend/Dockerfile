FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app.py config.py utils.py ./
COPY components ./components
COPY sections ./sections
COPY services ./services
COPY .streamlit ./.streamlit

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
