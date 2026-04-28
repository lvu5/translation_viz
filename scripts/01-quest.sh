# push to remote
rsync -azP --filter=":- .gitignore" --exclude .git/ . ltb:/home/zouhar/last-translation-benchmark/

python3 server --host-public "https://quest.ms.mff.cuni.cz/ltb/"