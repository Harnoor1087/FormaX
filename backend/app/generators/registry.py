from ..routing.format_router import default_router, FormatRouter
from .advisory import generate_advisory
from .social import generate_linkedin_post, generate_twitter_thread
from .executive import generate_executive_summary, generate_presentation
from .media import generate_infographic, generate_video_package

def register_all_generators(router: FormatRouter = default_router):
    """
    Registers the 7 standard generator modules defined in the FormaX AI Synopsis.
    Member 3 can register custom/extended generators by calling router.register(format, fn).
    """
    router.register("advisory", generate_advisory)
    router.register("linkedin_post", generate_linkedin_post)
    router.register("twitter_thread", generate_twitter_thread)
    router.register("executive_summary", generate_executive_summary)
    router.register("presentation", generate_presentation)
    router.register("infographic", generate_infographic)
    router.register("video_package", generate_video_package)

# Auto-register on import
register_all_generators()
