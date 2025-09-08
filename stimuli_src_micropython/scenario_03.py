# Scenario: trigger
def scenario(ctx):
    ctx.IN_t(1)
    ctx.IN_P_1V4()
    ctx.wait_ms(50)
    ctx.IN_t(0)
    ctx.IN_P_0V0()