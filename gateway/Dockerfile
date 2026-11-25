# Contexto de build = raiz do projeto (precisa da pasta web/ com a tela)
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY gateway/nginx.conf /etc/nginx/conf.d/default.conf
COPY web /usr/share/nginx/html
EXPOSE 8000
