from ..routing.format_router import default_router, FormatRouter
from ..ai.content_generator import content_generator
from ..schemas.request import OutputType
from .advisory import generate_advisory
from .social import generate_linkedin_post, generate_twitter_thread
from .executive import generate_executive_summary, generate_presentation
from .media import generate_infographic, generate_video_package

def register_all_generators(router: FormatRouter = default_router):
    """
    Registers the 7 standard generator modules defined in the FormaX AI Synopsis.
    Member 3 can register custom/extended generators by calling router.register(format, fn).
    """
    generators = {
        OutputType.ADVISORY: generate_advisory,
        OutputType.LINKEDIN_POST: generate_linkedin_post,
        OutputType.TWITTER_THREAD: generate_twitter_thread,
        OutputType.EXECUTIVE_SUMMARY: generate_executive_summary,
        OutputType.PRESENTATION: generate_presentation,
        OutputType.INFOGRAPHIC: generate_infographic,
        OutputType.VIDEO_PACKAGE: generate_video_package,
    }
    for output_type, template_generator in generators.items():
        router.register(
            output_type.value,
            lambda context, output_type=output_type, template_generator=template_generator:
                content_generator.generate(context, output_type, template_generator),
        )

# Auto-register on import
register_all_generators()
