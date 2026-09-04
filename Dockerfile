# THE GRID — L4 exhibit. Static play surface on HF Docker Spaces (port 7860).
# Not a Vite kernel. play.html is the runtime.
FROM python:3.12-slim
WORKDIR /app
COPY play.html index.html
COPY README.md ALIGN.md ./
ENV PORT=7860
EXPOSE 7860
CMD ["python", "-m", "http.server", "7860", "--bind", "0.0.0.0"]
