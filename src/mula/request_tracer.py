import json
from .text import Text

class RequestTracer:
    is_tracer_on = False # Set to True to enable request tracing
    truncated_length_request = -1 # Set to -1 no truncation
    truncated_length_response = 500

    @staticmethod
    def log_formatted(response, *args, **kwargs):
        if not RequestTracer.is_tracer_on:
            return
        color_status = RequestTracer._get_color_status(response.status_code)

        out  = str(Text.format('{*}',f"REQUEST {response.status_code}▶ ").set_background(color_status))
        out += str(Text.format('{*}',f" {response.request.method}"))
        out += str(Text.format('{/}',f" {response.url}\n"))
        
        out += f"  Headers: {json.dumps(dict(response.request.headers), indent=4, ensure_ascii=False)}\n"
        request_body = response.request.body
        
        if isinstance(request_body, bytes):
            try:
                request_body = json.dumps(request_body.decode(), indent=4, ensure_ascii=False)
            except:
                request_body = str(request_body)

        request_body = "None" if not request_body else RequestTracer.truncated_request(request_body)

        out += f"  Body: {request_body}\n"
        out += str(Text.format(' RESPONSE  ◀ ').set_background('B'))
        out += f"\n  Headers:\n{json.dumps(dict(response.headers), indent=4, ensure_ascii=False)}\n"

        try:
            parsed_response = response.json()
            response_body = json.dumps(parsed_response, indent=4, ensure_ascii=False)
        except ValueError:
            response_body = response.text
        
        response_body = "None" if not response_body else RequestTracer.truncated_response(response_body)
        out += f"  Body:\n{response_body}\n"
        print(out)
    
    @staticmethod
    def log_minified(response, *args, **kwargs):
        # TODO save in a log file based on an output directory
        if not RequestTracer.is_tracer_on:
            return
        out = f"REQUEST:{response.status_code}:{response.request.method}:{response.url}"
        print(out)

    @staticmethod
    def truncated_request(request_body):
        if len(request_body) > RequestTracer.truncated_length_request and RequestTracer.truncated_length_request > 0:
            request_body = f"{request_body[:RequestTracer.truncated_length_request]}" + " ... (truncated)"
        return request_body
    
    @staticmethod
    def truncated_response(response_body):
        if len(response_body) > RequestTracer.truncated_length_response and RequestTracer.truncated_length_response > 0:
            response_body = f"{response_body[:RequestTracer.truncated_length_response]}" + "  ... (truncated)"
        return response_body
        
    @staticmethod
    def _get_color_status(status_code):
        if status_code >= 400:
            return 'R'  # Red for errors
        elif status_code >= 300:
            return 'Y'  # Yellow for redirects
        elif status_code >= 200:
            return 'G'  # Green for success
        elif status_code >= 100:
            return 'B'  # Blue for informational responses
        else:
            return 'M'  # Default to magenta for unknown status codes
