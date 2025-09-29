# Prepare
#   duration_max_s=5
#
# Expected
#   enable_end_detected=True
#   enable_s=2s
#
def scenario(ctx):
    ctx.wait_s(2)
    ctx.disable()
