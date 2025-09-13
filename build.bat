docker build --platform=linux/amd64 -t news_crawler .
docker save -o news_crawler.tar news_crawler:latest