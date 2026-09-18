.PHONY: up down logs ps build restart clean init

init:
	cp -n .env.example .env || true
	@echo ">> แก้ไฟล์ .env ใส่ค่าจริงก่อนรัน make up"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

build:
	docker compose build

restart:
	docker compose restart

clean:
	docker compose down -v
