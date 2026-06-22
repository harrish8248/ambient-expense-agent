from google.adk.cli.fast_api import get_fast_api_app

app = get_fast_api_app(
    agents_dir="expense_agent",
    web=True,
    otel_to_cloud=False,
)

print("App state attributes:", dir(app.state))
try:
    print("app.state.session_service:", app.state.session_service)
except AttributeError:
    print("No session_service in app.state")

try:
    print("app.state.runner:", app.state.runner)
except AttributeError:
    print("No runner in app.state")
