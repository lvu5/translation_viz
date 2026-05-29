# push to remote
rsync -azP --filter=":- .gitignore" --exclude .git/ . ltb:/home/zouhar/last-translation-benchmark/

# pull db from remote
rsync -azP ltb:/home/zouhar/last-translation-benchmark/data/db.sqlite data/
rsync -azP ltb:/home/zouhar/submissions.json data/

python3 server --host-public "https://last-translation-benchmark.vilda.net" --host "0.0.0.0" --port 80