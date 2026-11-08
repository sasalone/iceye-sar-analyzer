# SAR Dark Vessel Kinematics & Wake Analyzer

Työkalu pimeiden alusten (AIS offline) todellisen sijainnin, koon, kulkusuunnan ja nopeuden määrittämiseen yhdestä X-kaistan SAR-tutkakuvasta hyödyntäen konenäköä ja Doppler-atsimuuttisiirtymää.

## Arkkitehtuuri
1. **Fetcher (`src/fetcher.py`):** Hakee STAC-katalogista SAR-kuvan metatiedot ja tallentaa valitun laivaleikkeen (ROI) paikalliseen välimuistiin.
2. **Detector (`src/detector.py`):** Segmentoi aluksen tutkaheijastuksen (dihedral) ja määrittää sen keskipisteen sekä mitat.
3. **Annotator (`src/annotator.py`):** Interaktiivinen työkalu heikon perävanan (wake) vektorin määrittämiseen.
4. **Physics (`src/physics.py`):** Laskee atsimuuttisiirtymästä ($\Delta x$) ja satelliitin rataparametreista aluksen nopeuden ja suunnan.
