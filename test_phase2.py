from core.component_toggle import parse_component_flags, build_execution_plan, check_stage_dependency
from config import RunConfig

# Test all flags on
flags = parse_component_flags('ScDbSbAi')
config = RunConfig(query='test', target_domain='test.com', mode='autonomous', scraper='direct', output_dir='results', test_injection=False, max_retries=3, max_pages=50)
plan = build_execution_plan(flags, config)

assert 'parsing' in plan.order
assert 'sandbox_execution' in plan.order
assert check_stage_dependency('ingestion', plan) == True

# Test partial
flags = parse_component_flags('SbAi')
plan = build_execution_plan(flags, config)
assert 'scraping' not in plan.order
assert 'sandbox_execution' in plan.order
assert check_stage_dependency('sandbox_execution', plan) == True

print('All Phase 2 tests passed!')
