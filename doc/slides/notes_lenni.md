# Notes Lenni

- apply knowledge and play out the attack
- we start with meltdown
- here is the attack code (show the code)

## Attack code

- the first block, we encode the secret byte from address 0xc000 into the cache
- we load, thus cache, the base address 0x1000 + secret byte
- we do this in the transient window before the first LB causes the rollback
- since the rollback is unaffected by the rollback, we can retrieve it

----

- the second block sets up for retrieving the secret byte
- r1 holds the shortest load offset and is initialised with 0x0000
- r2 holds the shortest load time and is initialised with 0xffff, the max value of a word
- r3 holds the current offset
- r4 holds the last offset we will probe


----

- the third block will probe the cache for a cached line
- we measure the time the load byte instr takes
- we load from the base 0x1000 plus the offset

----

- the fourth block will compare the load time with the previous shortest, and if applicable update the shortest load time and offset

---

- in the fift block, we increment to the next offset, and loop

----

- finally, after looping, we shift the fastest load offset to get the secret byte

---

- what do we see? (starting prog)
-

    step


- queue filled
-

    step

- rs filled
- explain rs meaning
- some entries wait for others

--- 

- retire - lets forward a bit
-

    retire

- shift retired first

--- 

- lets go back and see what happened before
-

    step -1

- both shift and load done
- load needs extra time in retire phase, due to checks
-

    continue
    show cache
    show mem 0xc000
---

- program will be continued after faulting instr.

---

- who wants to see me singlestep through the loop 256 times?
- i'll give you some hints though if you wanna try this at home

--- 

- you can use breakpoints
-

    break add 10
    continue

---

- and can modify the current index:
-

    step -1
    edit reg 3 0x410
    edit reg 4 0x420
    step

- why did I step out? 
- values are locked when issuing instructions

---

    show cache
    continue

- we ignore branch misprediction  
-

    continue

- now 0x410 is 'fastest'
-

    continue

- now 0x420 is fastest
-

    continue

- why pred error?
-


    continue


- another pred error, this time it was the loop!
- we see slli
-

    step
    step


----

    show cache

- cache sets x ways need to be big enough to prevent eviction

--- 

and here is the result:

MITIGATION

- how to exit vim? joke
-

    step
    step
    step
    step
    step
    step
