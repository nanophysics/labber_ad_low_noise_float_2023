def scenario():
    IN_disable(0)
    IN_P(IN_P_0V7)

    wait_ms(1000)
    
    IN_t(0)
    IN_P(IN_P_0V0)

    wait_ms(1000)

    IN_disable(1)
    IN_P(IN_P_1V4)

    wait_ms(1000)
    
    IN_t(1)
    IN_P(IN_P_0V0)

