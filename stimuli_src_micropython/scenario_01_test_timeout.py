# Prepare
#   duration_max_s=5
#
# Expected
#   timeout_detected=True
#   enable_s=5
#
def scenario(ctx):
    ctx.wait_s(10)
