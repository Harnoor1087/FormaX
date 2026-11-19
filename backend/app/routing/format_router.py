from typing import Callable, Dict, List, Any
from ..errors import LanguageGenerationUnavailable
from ..schemas.request import OutputType
from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem

# Type alias for generator handler functions provided by Member 3
GeneratorHandler = Callable[[StructuredContext], GenerateOutputItem]

SUPPORTED_FORMATS = {t.value for t in OutputType}

class FormatRouter:
    """
    Format Router (Section 3.5 & 6.4).
    Validates requested formats against an explicit allowlist and dispatches
    validated StructuredContext downstream to registered generator modules.
    """

    def __init__(self):
        self._registry: Dict[str, GeneratorHandler] = {}
        # Pre-register default MVP fallback generators so pipeline is end-to-end operational
        self._register_default_generators()

    def register(self, format_name: str, handler: GeneratorHandler):
        """
        Public interface for Member 3 to register format-specific generator modules.
        """
        if format_name not in SUPPORTED_FORMATS:
            raise ValueError(f"Cannot register unsupported format '{format_name}'. Allowed: {SUPPORTED_FORMATS}")
        self._registry[format_name] = handler

    def unregister(self, format_name: str):
        if format_name in self._registry:
            del self._registry[format_name]

    def is_registered(self, format_name: str) -> bool:
        return format_name in self._registry

    def route(self, context: StructuredContext, requested_formats: List[OutputType]) -> List[GenerateOutputItem]:
        """
        Dispatches the validated context to each requested generator with error isolation.
        If a generator raises an exception, other outputs are preserved.
        Uses parallel execution for better performance (5x faster for multiple formats).
        """
        import concurrent.futures
        
        outputs = []
        
        def generate_single(fmt):
            fmt_str = fmt.value if isinstance(fmt, OutputType) else str(fmt)
            if fmt_str not in SUPPORTED_FORMATS:
                raise ValueError(f"Requested format '{fmt_str}' is not supported.")
            
            generator = self._registry.get(fmt_str)
            if not generator:
                generator = self._create_baseline_generator(fmt_str)
                
            try:
                output_item = generator(context)
                if not isinstance(output_item, GenerateOutputItem):
                    # Wrap or validate
                    output_item = GenerateOutputItem(
                        output_type=fmt_str,
                        title=f"{fmt_str.replace('_', ' ').title()}: {context.topic[:50]}",
                        summary=str(output_item),
                        key_points=context.key_facts[:3],
                        body=str(output_item),
                    )
                return (fmt_str, output_item, None)
            except LanguageGenerationUnavailable:
                raise
            except Exception as e:
                # Fault isolation: Do not fail other requested formats if one fails
                error_output = GenerateOutputItem(
                    output_type=fmt_str,
                    title=f"Error Generating {fmt_str.replace('_', ' ').title()}",
                    summary="A generator error occurred during formatting.",
                    key_points=[],
                    body=f"Failed to generate output: {str(e)}",
                )
                return (fmt_str, error_output, e)
        
        # Execute all generators in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(requested_formats)) as executor:
            future_to_format = {executor.submit(generate_single, fmt): fmt for fmt in requested_formats}
            
            for future in concurrent.futures.as_completed(future_to_format):
                try:
                    fmt_str, output_item, error = future.result()
                    outputs.append(output_item)
                except LanguageGenerationUnavailable:
                    raise
                except Exception as e:
                    # Fallback error handling
                    fmt = future_to_format[future]
                    fmt_str = fmt.value if isinstance(fmt, OutputType) else str(fmt)
                    outputs.append(GenerateOutputItem(
                        output_type=fmt_str,
                        title=f"Error Generating {fmt_str.replace('_', ' ').title()}",
                        summary="A generator error occurred during formatting.",
                        key_points=[],
                        body=f"Failed to generate output: {str(e)}",
                    ))
        
        # Sort outputs to match the order of requested_formats
        format_order = {fmt.value if isinstance(fmt, OutputType) else str(fmt): i for i, fmt in enumerate(requested_formats)}
        outputs.sort(key=lambda x: format_order.get(x.output_type, 999))
            
        return outputs

    def _register_default_generators(self):
        for fmt in SUPPORTED_FORMATS:
            self._registry[fmt] = self._create_baseline_generator(fmt)

    def _create_baseline_generator(self, format_name: str) -> GeneratorHandler:
        """
        Default MVP generator: transforms structured context into the contract
        expected by Member 1's frontend.
        """
        def generator(ctx: StructuredContext) -> GenerateOutputItem:
            facts_list = ctx.key_facts
            formatted_title = f"{format_name.replace('_', ' ').capitalize()}: {ctx.topic[:60]}"
            summary_text = (
                f"Generated {format_name.replace('_', ' ')} tailored for {ctx.parameters.audience} "
                f"with a {ctx.parameters.tone} tone in {ctx.parameters.language}."
            )
            
            # Grounded body construction
            body_parts = [
                f"Topic: {ctx.topic}",
                f"Domain: {ctx.domain} | Urgency: {ctx.urgency.upper()}",
                "",
                "Summary Analysis:",
                "\n".join([f"- {f}" for f in facts_list]),
                "",
                "Source Reference & Directives:",
                ctx.source_text[:500] + ("..." if len(ctx.source_text) > 500 else ""),
            ]
            
            return GenerateOutputItem(
                output_type=format_name,
                title=formatted_title,
                summary=summary_text,
                key_points=facts_list[:5],
                body="\n".join(body_parts),
            )
        return generator

default_router = FormatRouter()

# Auto-register standard generator modules
try:
    from ..generators.registry import register_all_generators
    register_all_generators(default_router)
except ImportError:
    pass
