#!/usr/bin/env python3
"""
Bakaláři v3 API MCP Server
Poskytuje nástroje pro práci s Bakaláři školním systémem přes Model Context Protocol.
"""

import argparse
import asyncio
import json
import sys
import re
from datetime import datetime
from typing import Optional, Dict, Any
import aiohttp
from urllib import parse

from fastmcp import FastMCP

# Vytvoření MCP serveru
mcp = FastMCP("Bakaláři v3 API")

# Globální proměnné pro autentizaci
access_token: Optional[str] = None
refresh_token: Optional[str] = None
server_url: Optional[str] = None
username: Optional[str] = None
password: Optional[str] = None


class BakalariAuthError(Exception):
    """Chyba při autentizaci s Bakaláři API"""
    pass


class BakalariAPIError(Exception):
    """Obecná chyba API"""
    pass


async def authenticate() -> Dict[str, Any]:
    """
    Provede autentizaci s Bakaláři API pomocí username/password
    nebo refresh tokenu.
    """
    global access_token, refresh_token
    
    if not server_url:
        raise BakalariAuthError("Server URL není nastaven")
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    # Pokud máme refresh token, zkusíme ho použít
    if refresh_token:
        login_data = f"client_id=ANDR&grant_type=refresh_token&refresh_token={refresh_token}"
    elif username and password:
        login_data = f"client_id=ANDR&grant_type=password&username={username}&password={password}"
    else:
        raise BakalariAuthError("Nejsou k dispozici přihlašovací údaje")
    
    login_url = f"{server_url}/api/login"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(login_url, data=login_data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    access_token = data.get("access_token")
                    refresh_token = data.get("refresh_token")
                    return data
                elif response.status == 400:
                    error_data = await response.json()
                    raise BakalariAuthError(f"Chyba přihlášení: {error_data.get('error_description', 'Neznámá chyba')}")
                else:
                    raise BakalariAuthError(f"Chyba HTTP {response.status}")
        except aiohttp.ClientError as e:
            raise BakalariAuthError(f"Chyba připojení: {e}")


async def api_request(endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
    """
    Provede API požadavek s automatickou autentizací.
    """
    global access_token
    
    if not access_token:
        await authenticate()
    
    if not server_url:
        raise BakalariAPIError("Server URL není nastaven")
    
    url = f"{server_url}{endpoint}"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {access_token}"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, headers=headers, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    # Token expiroval, zkusíme refresh
                    await authenticate()
                    headers["Authorization"] = f"Bearer {access_token}"
                    async with session.request(method, url, headers=headers, **kwargs) as retry_response:
                        if retry_response.status == 200:
                            return await retry_response.json()
                        else:
                            error_text = await retry_response.text()
                            raise BakalariAPIError(f"API chyba {retry_response.status}: {error_text}")
                else:
                    error_text = await response.text()
                    raise BakalariAPIError(f"API chyba {response.status}: {error_text}")
        except aiohttp.ClientError as e:
            raise BakalariAPIError(f"Chyba připojení: {e}")


def infer_subject_from_theme(theme: str) -> str:
    """
    Inferuje předmět z tématu hodiny podle klíčových slov.
    """
    if not theme:
        return None
    
    theme_lower = theme.lower()
    
    # Matematika
    if any(word in theme_lower for word in ['nerovnic', 'interval', 'rovnic', 'funkc', 'integrál', 'derivac', 'logaritm', 'goniometri']):
        return "Matematika"
    
    # Čeština
    if any(word in theme_lower for word in ['souvětí', 'skladba', 'gramatik', 'pravopis', 'literatur', 'sloh', 'čtení', 'interpretac', 'rozbor', 'básn']):
        return "Český jazyk a literatura"
    
    # Fyzika
    if any(word in theme_lower for word in ['hydraulick', 'hydrostatick', 'tlak', 'síla', 'energie', 'pohyb', 'mechanik', 'elektřin', 'magnet']):
        return "Fyzika"
    
    # Dějepis
    if any(word in theme_lower for word in ['hospodářství', 'století', 'manufaktur', 'monarchie', 'absolutis', 'stavovsk', 'historie']):
        return "Dějepis"
    
    # Zeměpis
    if any(word in theme_lower for word in ['afrika', 'continent', 'západní', 'centrální', 'geografie', 'klima']):
        return "Zeměpis"
    
    # Angličtina/Němčina
    if any(word in theme_lower for word in ['časování', 'slovesa', 'gramatik']) and 'sloves' in theme_lower:
        return "Cizí jazyk"
    
    # Biologie
    if any(word in theme_lower for word in ['život', 'oblacích', 'organismus', 'buňka', 'ekologie']):
        return "Biologie"
    
    # Výtvarná výchova
    if any(word in theme_lower for word in ['maketa', 'pokoje', 'nábytek', 'dekorace', 'výtvarné']):
        return "Výtvarná výchova"
    
    # Hudební výchova  
    if any(word in theme_lower for word in ['flétnu', 'orffovy', 'nástroje', 'píseň', 'hudba']):
        return "Hudební výchova"
    
    # Film/Literatura
    if any(word in theme_lower for word in ['brendan', 'kellsu', 'tajemství', 'kniha', 'film']):
        return "Český jazyk a literatura"
    
    # Tělesná výchova
    if any(word in theme_lower for word in ['vybíjená', 'sport', 'tělocvik']):
        return "Tělesná výchova"
    
    # Test/zkouška
    if any(word in theme_lower for word in ['test', 'zkouška', 'opakování']):
        if 'prázdniny francouzů' in theme_lower:
            return "Český jazyk a literatura"
    
    # Prezentace
    if 'prezentace' in theme_lower:
        if 'záchranné stanice' in theme_lower:
            return "Biologie"
    
    return None


def get_subject_abbrev(subject: str) -> str:
    """
    Vrací zkratku předmětu.
    """
    if not subject:
        return None
    
    abbrevs = {
        "Matematika": "M",
        "Český jazyk a literatura": "Cj", 
        "Fyzika": "F",
        "Dějepis": "D",
        "Zeměpis": "Z",
        "Cizí jazyk": "Aj",
        "Biologie": "Bi",
        "Výtvarná výchova": "Vv",
        "Hudební výchova": "Hv",
        "Tělesná výchova": "Tv"
    }
    
    return abbrevs.get(subject, subject[:2])


def parse_change_description(description: str) -> Dict[str, str]:
    """
    Parsuje popis změny a extrahuje z něj předmět, učitele a místnost.
    """
    result = {}
    
    if not description:
        return result
    
    # Příklady:
    # "Spojeno: IT, Breginová Ivana, MMU (Aj, Lipinová Ivana, M2)"
    # "Suplování: Hennhofer Dennis (Tru)"
    # "Zrušeno (PCV, Czernek Pavel)"
    
    # Pattern pro "Spojeno:" 
    spojeno_match = re.search(r'Spojeno:\s*([^,]+),\s*([^,]+),\s*([^(]+)', description)
    if spojeno_match:
        result['predmet'] = spojeno_match.group(1).strip()
        result['ucitel'] = spojeno_match.group(2).strip()
        result['mistnost'] = spojeno_match.group(3).strip()
        return result
    
    # Pattern pro "Suplování:"
    supl_match = re.search(r'Suplování:\s*([^(]+)\s*\(([^)]+)\)', description)
    if supl_match:
        result['ucitel'] = supl_match.group(1).strip()
        original_teacher = supl_match.group(2).strip()
        return result
    
    # Pattern pro "Zrušeno"
    zruseno_match = re.search(r'Zrušeno\s*\(([^,]+),\s*([^)]+)\)', description)
    if zruseno_match:
        result['predmet'] = zruseno_match.group(1).strip()
        result['ucitel'] = zruseno_match.group(2).strip()
        return result
    
    return result


@mcp.tool()
async def rozvrh(datum: str = None) -> Dict[str, Any]:
    """
    Získá rozvrh pro zadané datum - aktuální rozvrh s dekódovanými informacemi.
    
    Args:
        datum: Datum ve formátu YYYY-MM-DD. Pokud není zadáno, použije se dnešní datum.
    
    Returns:
        Dict obsahující rozvrh pro zadaný den se základními informacemi (hodina, vyučující, předmět)
    """
    try:
        # Pokud není datum zadáno, použij dnešní
        if not datum:
            datum = datetime.now().strftime("%Y-%m-%d")
        
        # Validace formátu data
        try:
            parsed_date = datetime.strptime(datum, "%Y-%m-%d")
        except ValueError:
            return {
                "error": "Neplatný formát data. Použij YYYY-MM-DD.",
                "example": "2024-03-15"
            }
        
        # Získáme den v týdnu (1=pondělí, 5=pátek)
        day_of_week = parsed_date.weekday() + 1
        
        # Získáme aktuální rozvrh - je to kombinace stálého rozvrhu a změn
        actual_endpoint = f"/api/3/timetable/actual?date={datum}"
        actual_data = await api_request(actual_endpoint)
        
        # Vytvoření lookup tabulek z actual dat (obsahují všechny potřebné informace)
        hours_lookup = {hour.get("Id"): hour for hour in actual_data.get("Hours", [])}
        subjects_lookup = {subj.get("Id"): subj for subj in actual_data.get("Subjects", [])}
        teachers_lookup = {teacher.get("Id"): teacher for teacher in actual_data.get("Teachers", [])}
        rooms_lookup = {room.get("Id"): room for room in actual_data.get("Rooms", [])}
        
        # Najdeme hodiny pro zadaný den
        hodiny = []
        if "Days" in actual_data:
            for day in actual_data["Days"]:
                day_date = day.get("Date", "")
                if datum in day_date:
                    # Zpracujeme všechny hodiny (Atoms) pro tento den
                    for atom in day.get("Atoms", []):
                        hour_id = atom.get("HourId")
                        
                        # Základní informace z lookup tabulek
                        hour_info = hours_lookup.get(hour_id, {})
                        subject_info = subjects_lookup.get(atom.get("SubjectId"), {})
                        teacher_info = teachers_lookup.get(atom.get("TeacherId"), {})
                        room_info = rooms_lookup.get(atom.get("RoomId"), {})
                        
                        # Sestavíme hodinu s požadovanými informacemi
                        hodina = {
                            "hodina": hour_info.get("Caption", str(hour_id)),
                            "cas": f"{hour_info.get('BeginTime', '')} - {hour_info.get('EndTime', '')}" if hour_info.get('BeginTime') else None,
                            "predmet": subject_info.get("Name", ""),
                            "zkratka_predmetu": subject_info.get("Abbrev", ""),
                            "ucitel": teacher_info.get("Abbrev", ""),
                            "mistnost": room_info.get("Abbrev", ""),
                            "tema": atom.get("Theme", "")
                        }
                        
                        # Zpracování zrušených hodin
                        if atom.get("Change") and atom["Change"].get("ChangeType") == "Canceled":
                            hodina["zruseno"] = True
                            hodina["predmet"] = "ZRUŠENO"
                            hodina["zkratka_predmetu"] = "❌"
                            # Pro zrušené hodiny zkusíme extrahovat původní předmět z popisu
                            change_desc = atom["Change"].get("Description", "")
                            parsed = parse_change_description(change_desc)
                            if parsed.get("predmet"):
                                hodina["puvodni_predmet"] = parsed["predmet"]
                            if parsed.get("ucitel"):
                                hodina["puvodni_ucitel"] = parsed["ucitel"]
                        
                        # Inferuj předmět z tématu pokud není dostupný (jen pro nezrušené hodiny)
                        if not hodina.get("zruseno") and not hodina["predmet"] and hodina["tema"]:
                            inferred_subject = infer_subject_from_theme(hodina["tema"])
                            if inferred_subject:
                                hodina["predmet"] = inferred_subject
                                hodina["zkratka_predmetu"] = get_subject_abbrev(inferred_subject)
                        
                        # Přidej informaci o změně pokud existuje
                        if atom.get("Change"):
                            hodina["zmena"] = {
                                "typ": atom["Change"].get("ChangeType"),
                                "popis": atom["Change"].get("Description", "")
                            }
                        
                        hodiny.append(hodina)
                    break
        
        # Seřadíme hodiny podle HourId (hodina číslo)
        hodiny.sort(key=lambda h: int(h["hodina"]) if h["hodina"].isdigit() else 999)
        
        return {
            "datum": datum,
            "den_tydne": day_of_week,
            "hodiny": hodiny,
            "pocet_hodin": len(hodiny)
        }
        
    except BakalariAuthError as e:
        return {"error": f"Chyba autentizace: {e}"}
    except BakalariAPIError as e:
        return {"error": f"Chyba API: {e}"}
    except Exception as e:
        return {"error": f"Neočekávaná chyba: {e}"}


@mcp.tool()
async def staly_rozvrh() -> Dict[str, Any]:
    """
    Získá stálý rozvrh (základní rozvrh bez změn).
    
    Returns:
        Dict obsahující stálý rozvrh
    """
    try:
        endpoint = "/api/3/timetable/permanent"
        rozvrh_data = await api_request(endpoint)
        
        # Vytvoření lookup tabulek
        hours_lookup = {}
        subjects_lookup = {}
        teachers_lookup = {}
        rooms_lookup = {}
        groups_lookup = {}
        
        if "Hours" in rozvrh_data:
            for hour in rozvrh_data["Hours"]:
                hours_lookup[hour.get("Id")] = {
                    "caption": hour.get("Caption"),
                    "begin": hour.get("BeginTime"),
                    "end": hour.get("EndTime")
                }
        
        if "Subjects" in rozvrh_data:
            for subject in rozvrh_data["Subjects"]:
                subjects_lookup[subject.get("Id")] = {
                    "abbrev": subject.get("Abbrev"),
                    "name": subject.get("Name")
                }
        
        if "Teachers" in rozvrh_data:
            for teacher in rozvrh_data["Teachers"]:
                teachers_lookup[teacher.get("Id")] = {
                    "abbrev": teacher.get("Abbrev"),
                    "name": teacher.get("Name")
                }
        
        if "Rooms" in rozvrh_data:
            for room in rozvrh_data["Rooms"]:
                rooms_lookup[room.get("Id")] = {
                    "abbrev": room.get("Abbrev"),
                    "name": room.get("Name")
                }
        
        if "Groups" in rozvrh_data:
            for group in rozvrh_data["Groups"]:
                groups_lookup[group.get("Id")] = {
                    "abbrev": group.get("Abbrev"),
                    "name": group.get("Name")
                }
        
        # Zpracování stálého rozvrhu
        formatted_rozvrh = {
            "typ": "staly_rozvrh",
            "dny": [],
            "debug": {
                "lookup_count": {
                    "hours": len(hours_lookup),
                    "subjects": len(subjects_lookup),
                    "teachers": len(teachers_lookup),
                    "rooms": len(rooms_lookup),
                    "groups": len(groups_lookup)
                },
                "api_keys": list(rozvrh_data.keys()) if rozvrh_data else ["No data"],
                "has_days": "Days" in rozvrh_data if rozvrh_data else False,
                "days_count": len(rozvrh_data.get("Days", [])) if rozvrh_data else 0,
                "raw_data_sample": str(rozvrh_data)[:500] if rozvrh_data else "No data"
            }
        }
        
        if "Days" in rozvrh_data:
            for day in rozvrh_data["Days"]:
                day_info = {
                    "den_tydne": day.get("DayOfWeek"),
                    "den_cislo": day.get("Day"),
                    "hodiny": []
                }
                
                if "Atoms" in day:
                    # Seřadit atomy podle HourId
                    sorted_atoms = sorted(day["Atoms"], key=lambda x: x.get("HourId", 0))
                    
                    for atom in sorted_atoms:
                        # Překlad pomocí lookup tabulek
                        hour_id = atom.get("HourId")
                        subject_id = atom.get("SubjectId")
                        teacher_id = atom.get("TeacherId")
                        room_id = atom.get("RoomId")
                        
                        # Debug info pro první hodinu prvního dne
                        if len(formatted_rozvrh["dny"]) == 0 and len(day_info["hodiny"]) == 0:
                            formatted_rozvrh["debug"]["first_atom"] = {
                                "hour_id": hour_id,
                                "subject_id": subject_id,
                                "teacher_id": teacher_id,
                                "room_id": room_id,
                                "atom_keys": list(atom.keys())
                            }
                        
                        cas_info = hours_lookup.get(hour_id, {})
                        if cas_info.get('begin') and cas_info.get('end'):
                            cas = f"{cas_info.get('begin')} - {cas_info.get('end')}"
                        else:
                            cas = None
                        
                        subject_info = subjects_lookup.get(subject_id, {})
                        predmet = subject_info.get("name")
                        zkratka_predmetu = subject_info.get("abbrev")
                        
                        teacher_info = teachers_lookup.get(teacher_id, {})
                        ucitel = teacher_info.get("abbrev")
                        if not ucitel and teacher_info.get("name"):
                            # Zkus vzít příjmení z celého jména
                            full_name = teacher_info.get("name")
                            ucitel = full_name.split()[-1] if full_name else None
                        
                        room_info = rooms_lookup.get(room_id, {})
                        mistnost = room_info.get("abbrev")
                        
                        group_ids = atom.get("GroupIds", [])
                        skupina = None
                        if group_ids:
                            group_info = groups_lookup.get(group_ids[0], {})
                            skupina = group_info.get("abbrev")
                        
                        hodina_info = {
                            "hodina": cas_info.get("caption") if cas_info else str(hour_id),
                            "cas": cas,
                            "predmet": predmet,
                            "zkratka_predmetu": zkratka_predmetu,
                            "ucitel": ucitel,
                            "mistnost": mistnost,
                            "skupina": skupina
                        }
                        day_info["hodiny"].append(hodina_info)
                
                formatted_rozvrh["dny"].append(day_info)
        
        return formatted_rozvrh
        
    except BakalariAuthError as e:
        return {"error": f"Chyba autentizace: {e}"}
    except BakalariAPIError as e:
        return {"error": f"Chyba API: {e}"}
    except Exception as e:
        return {"error": f"Neočekávaná chyba: {e}"}


def main():
    """Hlavní funkce pro spuštění MCP serveru"""
    parser = argparse.ArgumentParser(description="Bakaláři v3 API MCP Server")
    parser.add_argument("--user", required=True, help="Uživatelské jméno")
    parser.add_argument("--password", required=True, help="Heslo")
    parser.add_argument("--url", default="skola.bakalari.cz", help="URL Bakaláři serveru")
    
    args = parser.parse_args()
    
    # Nastavení globálních proměnných
    global username, password, server_url
    username = args.user
    password = args.password
    
    # Přidání https:// prefixu pokud chybí
    url = args.url.rstrip('/')
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    server_url = url
    
    # Spuštění MCP serveru
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
