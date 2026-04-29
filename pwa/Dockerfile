FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=http://localhost:5000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM python:3.11-slim

WORKDIR /srv/pwa

COPY --from=build /app/dist ./dist

EXPOSE 4173

CMD ["python", "-m", "http.server", "4173", "-d", "/srv/pwa/dist"]