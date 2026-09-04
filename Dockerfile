FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev=false
COPY . .
ENV HOST=0.0.0.0
ENV PORT=7860
EXPOSE 7860
CMD ["node", "scripts/with-app-env.mjs", "vite", "dev", "--host", "0.0.0.0", "--port", "7860"]
