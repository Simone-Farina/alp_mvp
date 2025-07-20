print tables in database

python - <<'PY'
from sqlalchemy import inspect
from alp.db.session import engine
print("Tables:", inspect(engine).get_table_names())
PY
