.PHONY: all launch stop clean

all:

launch:
	docker-compose up --build -d

stop:
	docker-compose down

clean:
	docker-compose down -v