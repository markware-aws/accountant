from mangum import Mangum
from main import app

# Lambda entry point
# Deploy with Lambda Function URL, InvokeMode: RESPONSE_STREAM
handler = Mangum(app, lifespan="off")
