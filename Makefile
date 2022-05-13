PROCS =$(shell nproc)
MAKEFLAGS += --jobs=$(PROCS)
IN_DIR=in/Cores
OUT_DIR=out
IN_FILES=$(wildcard $(IN_DIR)/*.xml)
OUT_FILES=$(IN_FILES:$(IN_DIR)/%.xml=$(OUT_DIR)/%.svd)
INTER_FILES=$(IN_FILES:$(IN_DIR)/%.xml=$(OUT_DIR)/%.xml)

SAXONHE_PATH=/usr/share/java/Saxon-HE.jar

XLST_FILE=./ads2svd.xslt

#$(info OUTFILES   $(OUT_FILES) )

.PHONY: clean all
#uncomment to keep the intermediate xml files
.SECONDARY: $(INTER_FILES)

all: $(OUT_DIR) $(OUT_FILES)

$(OUT_DIR)/%.svd : $(IN_DIR)/%.xml
	python convert.py $< $@

clean:
	rm out/*
