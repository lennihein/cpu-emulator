.DEFAULT_GOAL := docker

current_dir = $(shell pwd)

docker:
	rm lab.pdf -f
	docker run --rm -it -v $(current_dir)/:/doc lennihein/markdown2pdf:latest

native: 
	./build.sh