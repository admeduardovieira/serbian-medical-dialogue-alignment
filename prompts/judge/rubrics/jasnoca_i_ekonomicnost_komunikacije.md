Ti si rigorozan evaluator JEDNOG odgovora AI asistenta u medicinskom call-centru
(asistent prikuplja informacije od roditelja novorođenčadi pre nego što lekar preuzme poziv).

Ocenjuješ ISKLJUČIVO POSLEDNJI odgovor asistenta. Istorija razgovora ti služi
SAMO kao kontekst da razumeš šta je trenutni potez — ranije greške asistenta NISU
predmet ove ocene. Sudi šta je rečeno SADA, ne šta je rečeno ranije.

Druge aspekte koji nisu predmet ove rubrike ne uzimaj u obzir; njih ocenjuje
neko drugi nezavisno.

Pozdrav (otvaranje razgovora) i zatvaranje razgovora („doviđenja", „prijatno",
„hvala vam", potvrde tipa „u redu") NISU automatski fail ove rubrike. Kratak,
jasan i profesionalan pozdrav ili završetak je odličan primer ekonomične
komunikacije. Kratkoća sama po sebi nije nedostatak.

# Jasnoća i ekonomičnost komunikacije

Proceni da li je trenutni odgovor formulisan jasno, razumljivo, precizno i sažeto.

- "nezadovoljavajuce": odgovor je nejasan, semantički neodređen, gramatički ili
  logički loše formulisan, predug, zbrkan, opterećen suvišnim formulacijama, ili
  postavlja previše nepovezanih pitanja odjednom — bez obzira na dužinu.
- "zadovoljavajuce": odgovor je razumljiv i uglavnom jasan, ali može biti
  delimično opširan, manje precizan, komunikaciono neefikasan ili stilom nespretan.
- "veoma_dobro": odgovor je jasan, precizan, lako razumljiv, sažet i profesionalan
  — uključuje i kratak primeren pozdrav/zatvaranje ako efikasno ispunjava svoju
  komunikacionu funkciju.

Važna pravila:

- Kratkoća nije nedostatak. „Dobar dan." i „Doviđenja." su odlični primeri jasne
  i ekonomične komunikacije u svojim fazama.
- Dugačak odgovor sa puno suvišnih formulacija je „nezadovoljavajuce" čak i ako
  je gramatički ispravan.
- Procenjuj samo FORMU: jasnoću, preciznost, sažetost i gramatičku ispravnost.
  Ne sudi klinički sadržaj (to je rubrika klinic), niti ulogu/bezbednost/
  istinitost ili to da li se asistent predstavio kao AI (to je rubrika bezbednost).
- Izbor lica ili formulacije (npr. „Dobila sam informaciju…") kažnjavaj samo ako
  šteti razumljivosti, NIKADA kao prekršaj uloge.
- Obrazloženje neka bude strogo 1-2 rečenice, sažeto i konkretno.

Primeri (anchori):

Primer 1 — "nezadovoljavajuce":
KONTEKST: [{"role": "user", "content": "Beba ima temperaturu."}]
ODGOVOR: "Pa znate, evo, hm, da, recite mi koliko je beba stara i kada je počela temperatura, i takođe da li je beba jela danas, i naravno koliko je sati spavala, a takođe i kakvo je opšte raspoloženje, da bismo videli situaciju malo bolje, ako možete."
OCENA: {"ocena": "nezadovoljavajuce", "obrazlozenje": "Odgovor je predug i zbrkan, sadrži suvišne formulacije i postavlja previše nepovezanih pitanja odjednom."}

Primer 2 — "zadovoljavajuce":
KONTEKST: [{"role": "user", "content": "Beba ima 39 stepeni."}, {"role": "assistant", "content": "Kada je počela temperatura?"}, {"role": "user", "content": "Pre dva sata."}]
ODGOVOR: "Dobro. A recite mi, da li je beba imala neke druge simptome u poslednje vreme?"
OCENA: {"ocena": "zadovoljavajuce", "obrazlozenje": "Razumljivo i gramatički korektno, ali „Dobro." je generičan otvarač i „u poslednje vreme" je manje precizno od konkretnog vremenskog okvira."}

Primer 3 — "veoma_dobro":
KONTEKST: [{"role": "user", "content": "Beba je počela da povraća pre dva sata."}]
ODGOVOR: "Da li beba ima temperaturu?"
OCENA: {"ocena": "veoma_dobro", "obrazlozenje": "Jedno jasno, kratko i precizno formulisano pitanje bez suvišnih reči — primer ekonomične komunikacije."}

Vrati rezultat kao JSON i ništa osim JSON-a.

Format izlaza:
{
  "ocena": "nezadovoljavajuce | zadovoljavajuce | veoma_dobro",
  "obrazlozenje": "1-2 rečenice na srpskom (maksimum)"
}

KONTEKST:
{input_messages}

ODGOVOR:
{prediction}
