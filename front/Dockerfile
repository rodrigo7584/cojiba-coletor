# Etapa 1: Build
FROM node:18-alpine AS builder

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de configuração
COPY package.json package-lock.json* ./

# Instalar dependências
RUN npm install --frozen-lockfile

# Copiar código da aplicação
COPY . .

# Gerar build de produção
RUN npm run build

# Etapa 2: Produção
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV production

# Copiar apenas o necessário do build
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Expor porta padrão do Next.js
EXPOSE 3000

# Comando para rodar
CMD ["npm", "start"]
