python ./Docs/extract_common_server_js.py
jsdoc2md --json ./Docs/commonServerJsDoc.js > ./Docs/commonServerJsDoc.json
python ./Docs/common_server_docs.py
