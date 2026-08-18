.PHONY: c clean

c: clean

clean:
	rm -rf -- public resources exampleSite/public exampleSite/resources tmp
	rm -f -- .hugo_build.lock exampleSite/.hugo_build.lock
	find bin tests -type d -name __pycache__ -prune -exec rm -rf -- {} +
	find bin tests -type f -name '*.py[cod]' -delete
	find . -name .git -prune -o -type f -name .DS_Store -exec rm -f -- {} +
