# Evaluation {#sec:evaluation}

todo

    what kind of system do we need/ did we use to run this?
        which python Version?
        which program version ? git commit
        other dependencies?

## Example Program {#sec:evaluation_example}

todo

        brief example program showing all the features in a "normal" execution, e.g. adding stuff

## Meltdown Demonstration {#sec:evaluation_meltdown}

todo

            show example program

            maybe compare to example program for real life architecture from SCA or literature (Gruss) if available

            explain which Meltdown variant it implements

            briefly highlight which components (we expect to) interact to make it work

            how well does it work?

## Spectre Demonstration {#sec:evaluation_spectre}

todo

            same as Meltdown

## Mitigations Demonstration {#sec:evaluation_mitigations}

todo

            it is known which mitigations exist, here is what we have in our emulator:

            what is possible in our program as is
                planned:    cache flush: microcode -> config file
                            mfence im assembler (normally in compiler)
                            aslr directly in program -> config (es gibt ja auch mitigations, die keine echte mitigation sind; nice to have -> könnte demonstrieren dass es nicht der Fall ist; war eh schon einige Jahre vor Meltdown vorhanden/ in Gebrauch; KSLR brachen kann man auch als Angriff verkaufen)
                            flush IQ -> passiert eh schon, ist das überhaupt eine echte mitigation?
                            disable speculation (nice to have, lassen wir weg)-> config
                            out of order -> in config RS mit nur einem Slot

            is our meltdown/ spectre variant still possible?
            ggf. how does this affect the performance?
            vorsichtig sein, dass man dann auch die richtige Frage für die Antwort stellt
                in real life (already in background)
                in our program

            what would be the necessary steps/ changes to the program for further mitigations
                compare to changes in hardware by the manufacturers
