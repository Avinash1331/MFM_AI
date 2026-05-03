FROM node:20-alpine

WORKDIR /app

# Install deps first for caching
COPY package.json yarn.lock* ./
RUN yarn install --frozen-lockfile || yarn install

COPY . .

EXPOSE 3000
ENV WDS_SOCKET_PORT=0
CMD ["yarn", "start"]
