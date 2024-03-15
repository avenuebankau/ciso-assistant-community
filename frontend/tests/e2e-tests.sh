#! /usr/bin/env bash
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DB_DIR=$APP_DIR/backend/db
DB_NAME=test-database.sqlite3

SCRIPT_LONG_ARGS=()
SCRIPT_SHORT_ARGS=()
TEST_PATHS=()

BACKEND_PORT=8173

for arg in "$@"
do
    if [[ $arg == --port=* ]]; then
        BACKEND_PORT="${arg#*=}"
    elif [[ $arg == --* ]]; then
        SCRIPT_LONG_ARGS+=("$arg")
    elif [[ $arg == -* ]]; then
        SCRIPT_SHORT_ARGS+=("$arg")
    elif [[ $arg != -* ]]; then
        TEST_PATHS+=("$arg")
    fi
done

if [[ " ${SCRIPT_SHORT_ARGS[@]} " =~ " -h " ]] || [[ " ${SCRIPT_LONG_ARGS[@]} " =~ " --help " ]]; then
    echo "Usage: e2e-tests.sh [options] [test_path]"
    echo "Run the end-to-end tests for the CISO Assistant application."
    echo "Options:"
    echo "  --browser=NAME          Run the tests in the specified browser (chromium, firefox, webkit)"
    echo "  --global-timeout=MS     Maximum time this test suite can run in milliseconds (default: unlimited)"
    echo "  --grep=SEARCH           Only run tests matching this regular expression (default: \".*\")"
    echo "  --headed                Run the tests in headful mode"
    echo "  -h                      Show this help message and exit"
    echo "  --list                  List all the tests"
    echo "  --port=PORT             Run the backend server on the specified port (default: $BACKEND_PORT)"
    echo "  --project=NAME          Run the tests in the specified project"
    echo "  -q                      Quick mode: execute only the tests 1 time with no retries and only 1 project"
    echo "  --repeat-each=COUNT     Run the tests the specified number of times (default: 1)"
    echo "  --retries=COUNT         Set the number of retries for the tests"
    echo "  --timeout=MS            Set the timeout for the tests in milliseconds"
    echo "  -v                      Show the output of the backend server"
    echo -e "  --workers=COUNT         Number of concurrent workers or percentage of logical CPU cores, use 1 to run in a single worker (default: 1)"
    echo "                          Be aware that increasing the number of workers may reduce tests accuracy and stability"
    exit 0
fi

if python -c "import socket;exit(0 if 0 == socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('127.0.0.1',$BACKEND_PORT)) else 1)" ; then
    echo "The port $BACKEND_PORT is already in use!"
    echo "Please stop the running process using the port or change the backend test server port using --port=PORT and try again."
    exit 1
fi

cleanup() {
    echo -e "\nCleaning up..."
    if [ -n $BACKEND_PID ] ; then
        kill $BACKEND_PID > /dev/null 2>&1
        echo "| backend server stopped"
    fi
    if [ -f $DB_DIR/$DB_NAME ] ; then
        rm $DB_DIR/$DB_NAME
        echo "| test database deleted"
    fi
    if [ -d $APP_DIR/frontend/tests/utils/.testhistory ] ; then
        rm -rf $APP_DIR/frontend/tests/utils/.testhistory
        echo "| test data history removed"
    fi
    trap - SIGINT SIGTERM EXIT
    echo "Cleanup done"
    exit 0
}

finish() {
    echo "Test successfully completed!"
    cleanup
}

trap cleanup SIGINT SIGTERM
trap finish EXIT

echo "starting backend server..."
unset POSTGRES_NAME POSTGRES_USER POSTGRES_PASSWORD
export CISO_ASSISTANT_URL=http://localhost:4173
export ALLOWED_HOSTS=localhost
export DJANGO_DEBUG=True
export DJANGO_SUPERUSER_EMAIL=admin@tests.com
export DJANGO_SUPERUSER_PASSWORD=1234
export SQLITE_FILE=db/$DB_NAME

cd $APP_DIR/backend/
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --noinput
if [[ " ${SCRIPT_SHORT_ARGS[@]} " =~ " -v " ]] ; then
    nohup python manage.py runserver $BACKEND_PORT > $APP_DIR/frontend/tests/utils/.testbackendoutput.out 2>&1 &
    echo "You can view the backend server output at $APP_DIR/frontend/tests/utils/.testbackendoutput.out"
else
    nohup python manage.py runserver $BACKEND_PORT > /dev/null 2>&1 &
fi
BACKEND_PID=$!
echo "Test backend server started on port $BACKEND_PORT (PID: $BACKEND_PID)"

echo "Starting playwright tests"
export ORIGIN=http://localhost:4173
export PUBLIC_BACKEND_API_URL=http://localhost:$BACKEND_PORT/api

cd $APP_DIR/frontend/

if (( ${#TEST_PATHS[@]} == 0 )); then
    echo "running every functional test"
else
    echo "running tests: ${TEST_PATHS[@]}"
fi
if (( ${#SCRIPT_LONG_ARGS[@]} == 0 )); then
    echo "without args"
else
    echo "with args: ${SCRIPT_LONG_ARGS[@]}"
fi

if [[ " ${SCRIPT_SHORT_ARGS[@]} " =~ " -q " ]] ; then
    npx playwright test ./tests/functional/"${TEST_PATHS[@]}" -x --project=chromium "${SCRIPT_LONG_ARGS[@]}"
else
    npx playwright test ./tests/functional/"${TEST_PATHS[@]}" "${SCRIPT_LONG_ARGS[@]}"
fi
