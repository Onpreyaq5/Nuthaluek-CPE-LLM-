FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_USE_MOCKS=true
ENV VITE_USE_MOCKS=$VITE_USE_MOCKS
RUN npm run build

FROM nginx:stable-alpine
# ค่าตั้งต้นชี้กลับมาที่ตัว container เอง ซึ่ง proxy ไม่ติด
# docker-compose ตั้งทับเป็น http://api_backend:8000 ให้แล้ว
ENV API_UPSTREAM=http://api_backend:8000
RUN apk add --no-cache curl
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3   CMD curl -fsS http://localhost/ || exit 1
