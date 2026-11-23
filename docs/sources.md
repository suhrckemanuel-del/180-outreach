# Candidate sources (ticket 07)

Checked 2026-11-21 with plain HTTP (Firecrawl had no credits left; not needed). "Terms" means
robots.txt plus the site's own terms or disclaimer page. Scripts are in `tools/sources/`; run order
below, because the first source to claim a domain sets its segment.

| Source | URL checked | Name | Website | City | Size / income | Download or paging | Terms | Verdict |
|---|---|---|---|---|---|---|---|---|
| Aedes members | https://aedes.nl/vereniging/de-woningcorporaties-die-lid-zijn-van-aedes, data at https://aedes.nl/kaarten?map=372 | yes | yes | yes (address) | no (PDF lists give only name and place) | one GeoJSON request, no login | robots.txt allows, crawl-delay 5 | **kept**: `aedes.py`, Rotterdam region (Rijnmond + Delft neighbours) |
| Social Enterprise NL members | https://social-enterprise.nl/wp-json/wp/v2/lid, pages https://social-enterprise.nl/lid/<slug>/ | yes | yes ("Kijk op de website") | yes (Vestigingsplaats) | no (branche and impact area only) | public WordPress API, 464 members, then one page each at 1.5 s | robots.txt allows; terms reserve copyright on their texts and images only. We keep facts (name, site, city), no text | **kept**: `social_enterprise_nl.py`, all NL |
| ANBI register (Belastingdienst) | https://belastingdienst.nl/wps/wcm/connect/bldcontentnl/themaoverstijgend/brochures_en_publicaties/open_data_anbi, file https://download.belastingdienst.nl/data/anbi/anbi.zip | yes | yes (nearly every row) | yes (vestigingsplaats) | no | one zip (XML, 54,487 rows), refreshed weekly, no login | open data, licence CC0, no attribution needed | **kept**: `anbi.py`, Delft + Rotterdam (`--region` adds the neighbours) |
| Gemeente Rotterdam subsidy list | https://www.watdoetdegemeente.rotterdam.nl/jaarstukken-2024/jaarverslag-paragrafen/subsidies/ | yes | **no** | no | **yes**: amount paid in 2024 per recipient | one HTML page, ~1,400 rows | public annual accounts; robots.txt allows | **kept as enrichment**: `rotterdam_subsidies.py` adds no rows, writes the amount into `size_hint` of matching targets (size signal + known funding source) |
| CBF register (erkende goede doelen) | https://cbf.nl/register-erkende-goede-doelen, https://cbf.nl/proclaimer-privacy, https://cbf.nl/data | yes | via each "paspoort" page | yes | yes (financial figures on paspoort pages) | one long HTML page lists every organisation | **disclaimer forbids copying**: "niet toegestaan de informatie anders dan voor persoonlijk gebruik te verspreiden of te kopiëren zonder schriftelijke toestemming van het CBF"; datasets and API only on request via data@cbf.nl, under conditions and possibly costs | **dropped, waiting for Manuel**: no script. Option: ask data@cbf.nl for API access |
| Gemeente Delft subsidy recipients | searched delft.nl, lokaleregelgeving.overheid.nl, officielebekendmakingen.nl | - | - | - | - | no recipient list published (only the rules and forms; the last list found is a 2009 council appendix) | - | **dropped**: nothing to download |
| Funding-radar digests | `Desktop/funding-radar-*.md` (2026-05-23 to 2026-11-21) | yes | **no** (news link and a LinkedIn search link) | sometimes | round size | local files | own data | **dropped**: 19 NL entries in six months (~15 unique), none in Delft or Rotterdam, venture-backed tech start-ups rather than impact organisations |

## Rows per source and segment (run 2026-11-21)

Run order: `aedes.py`, `social_enterprise_nl.py`, `anbi.py`, then `rotterdam_subsidies.py`.

| Source | Segment | Delft + Rotterdam | Rotterdam region / Haaglanden | Rest of NL | Total |
|---|---|---|---|---|---|
| aedes | woningcorporatie | 7 | 19 | 0 | 26 |
| social_enterprise_nl | social_enterprise | 37 | 34 | 391 | 462 |
| anbi | nonprofit | 1,308 | 0 (run `--region` to add) | 0 | 1,308 |
| **all** | | **1,352** | 53 | 391 | **1,796** |

All 1,796 rows are `status: new` and have their own website. `rotterdam_subsidies.py` matched 225
Rotterdam rows to the municipality's 2024 list (1,248 recipients) and wrote the amount into `size_hint`.
ANBI filtered out: 366 ended, 310 religious/school/support foundations, 155 on a shared platform
domain, 38 without an own website; 42 duplicate domains. Social Enterprise NL: 2 duplicates.

Worth it so far: ANBI for volume, Social Enterprise NL for the segment test (but only 37 in
Delft/Rotterdam, so batch 2+ of social enterprises must go to the region or the rest of NL), Aedes
for the few corporations, the Rotterdam list as the only size and funding signal we have.

## Filters in code (no model reads a page)

- Every source: the website must be the organisation's own domain (no Facebook, LinkedIn, Google
  Sites, shared ANBI publishing platforms); de-duplicated on the domain across sources, against
  `pipeline.yaml` and against `private/suppression.private.yaml`.
- ANBI: ANBI status ended or withdrawn; churches, parishes, mosques and other congregations;
  schools, universities and the municipality; "Vrienden van" and support foundations; a host shared
  by 5 or more ANBIs nationally (a platform or umbrella, not one organisation's site).
- No source gives staff counts. National giants cannot be cut by income without CBF; the researcher
  rejects them (its REJECT rule), and `size_hint` from the Rotterdam list shows the large ones.

## Sort order

`status: new` first, then Delft and Rotterdam, then the Rotterdam region and Haaglanden, then the rest
of NL; within each, rows with a known `size_hint` first. `python tools/sources/mark.py --pick ...`
prints the next batch by that order.
