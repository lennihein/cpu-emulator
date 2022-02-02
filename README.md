# CPU-Emulator with Transient Execution

[![pipeline status](https://git.cs.uni-bonn.de/boes/lab_transient_ws_2122/badges/main/pipeline.svg)](https://git.cs.uni-bonn.de/boes/lab_transient_ws_2122/-/commits/main)

## Using Autopep8

```bash
autopep8 . --recursive --in-place --pep8-passes 2000 --aggressive --verbose
```

## Coding Conventions 

Zusammenfassung von https://www.python.org/dev/peps/pep-0008/

### Code Layout

#### Einrückung: 
    4 Leerzeichen pro Level (keine Tabs)

#### Zeilenlänge:
    höchstens 79 Zeichen pro Zeile, 72 in Textblöcken

#### Leerzeilen:	
    2 Leerzeilen um Klassendefinitionen und Top-Level-Funktionen
    1 Leerzeile um Funktionsdefinitionen in einer Klassendefinitionen
    sparsam im Funktionscode um Sinneinheiten zu trennen
    
#### Imports:
    1 import pro Zeile
    nach Modulkommentaren und Docstrings, vor globalen Variablen und Konstanten
    durch Leerzeilen in Standard Lib, 3rd party und local unterteilt
    wenn möglich absolute imports verweden
    keine wildcard imports (*) verwenden
		
### Kommentare

    ganze Sätze

#### Blockkommentare:
    selbes Einrückunslevel wie der Code
    jede Zeile startet mit # und einem Leerzeichen
    Leerzeilen starten auch mit #
    
#### Docstrings
    abschließende """ bilden eine eigene Zeile
    Ausnahme: Einzeiler
    ggf. mehr Details: https://www.python.org/dev/peps/pep-0257/
        
        
### Naming Conventions

    l und o nicht als einzelne Buchstanben verwenden, da Verwechslungsgefahr mit 1 und 0

#### Modulnamen:
    snake_case: nur Kleinbuchstaben mit Unterstrichen
    
#### Klassennamen:
    CamelCase: mit Großbuchstaben am Anfang
    Akronyme wie z.B. HTTPS komplett groß
    
#### Typ-Variablen: 
    CamelCase
    
#### Exception-Namen:
    folgt der Namenskonvention für Klassendefinitionen
    ggf. mit Suffix Error
    
#### globale Variablen:
    folgt der Namenskonvention für Funktionen
    ggf. mit __all__ verhindern, dass sie exportiert werden
    
#### Funktionen und Variablen:
    Funktionen: snake_case
    Variablen: folgen der Namenskonvention für Funktionen
    
#### Methodennamen und Instanzenvariablen:
    snake_case wie bei Funktionen
    _ am Anfang des Namens für non-public Methoden und Instanzvariablen
    
#### Argumente von Funktionen und Methoden:
    self erstes Argument für Instanzenmethoden
    cls erstes Argument Klassenmethoden	
    
#### Konstanten:
    NUR_GROSSBUCHSTABEN 
    
### Programmierempfehlungen
    
    Funktionen die an einer Stelle einen tatsächlichen Ausdruck zurück geben, sollte dies an allen Stellen tun
    ggf. None zurückgeben

#### Funktionsannotationen:
    sollten PEP 484 folgen
    
#### Variablenannotationen:
    ein Leerzeichen nach dem :
    kein Leerzeichen vor dem :
    bei Zuweisungen ein Leerzeichen auf jeder Seite des Gleichheitszeichens


#### Funktionsannotationen:
    sollten PEP 484 folgen
    
#### Variablenannotationen:
    ein Leerzeichen nach dem :
    kein Leerzeichen vor dem :
    bei Zuweisungen ein Leerzeichen auf jeder Seite des Gleichheitszeichens
