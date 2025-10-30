# Makefile for Sphinx documentation

SPHINXBUILD   = sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

html:
	@$(SPHINXBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html"

clean:
	rm -rf $(BUILDDIR)

.PHONY: help Makefile html clean
