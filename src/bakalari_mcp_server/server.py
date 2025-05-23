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
                        # Používáme konzistentně plné jméno učitele, pokud není k dispozici, použijeme zkratku
                        teacher_name = teacher_info.get("Name", "")
                        teacher_abbrev = teacher_info.get("Abbrev", "")
                        
                        hodina = {
                            "hodina": hour_info.get("Caption", str(hour_id)),
                            "cas": f"{hour_info.get('BeginTime', '')} - {hour_info.get('EndTime', '')}" if hour_info.get('BeginTime') else None,
                            "predmet": subject_info.get("Name", ""),
                            "zkratka_predmetu": subject_info.get("Abbrev", ""),
                            "ucitel": teacher_name if teacher_name else teacher_abbrev,
                            "ucitel_zkratka": teacher_abbrev,
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
                        
                        # Pokud je změna, přidáme informaci o změně (NEPŘEPISUJEME učitele z API)
                        if atom.get("Change"):
                            change_desc = atom["Change"].get("Description", "")
                            
                            hodina["zmena"] = {
                                "typ": atom["Change"].get("ChangeType"),
                                "popis": change_desc
                            }
                        
                        hodiny.append(hodina)
                    break
        
        # Seřadíme hodiny podle HourId (hodina číslo)
        hodiny.sort(key=lambda h: int(h["hodina"]) if h["hodina"].isdigit() else 999)
        
        return {
            "datum": datum,
            "den_tydne": day_of_week,
            "hodiny": hodiny,
            "pocet_hodin": len(hodiny),
            "debug_teachers": {
                "lookup": [(k, v.get("Name"), v.get("Abbrev")) for k, v in teachers_lookup.items()],
                "sample_teacher": list(teachers_lookup.values())[0] if teachers_lookup else None
            }
        }
        
    except BakalariAuthError as e:
        return {"error": f"Chyba autentizace: {e}"}
    except BakalariAPIError as e:
        return {"error": f"Chyba API: {e}"}
    except Exception as e:
        return {"error": f"Neočekávaná chyba: {e}"}


@mcp.tool()
async def absence() -> Dict[str, Any]:
    """
    Získá informace o absencích studenta.
    
    Returns:
        Dict obsahující absence podle dní a podle předmětů s detailními statistikami
    """
    try:
        endpoint = "/api/3/absence/student"
        absence_data = await api_request(endpoint)
        
        # Zpracování dat o absencích
        formatted_absence = {
            "typ": "absence",
            "prah_procent": absence_data.get("PercentageThreshold", 0),
            "absence_podle_dni": [],
            "absence_podle_predmetu": [],
            "souhrn": {
                "celkem_dni": 0,
                "dny_s_absenci": 0,
                "celkove_statistiky": {
                    "nevyreseno": 0,
                    "ok": 0,
                    "zmeskano": 0,
                    "pozdni_prichod": 0,
                    "brzy_odchod": 0,
                    "skolni_akce": 0,
                    "distancni_vyuka": 0
                }
            }
        }
        
        # Zpracování absencí podle dní
        if "Absences" in absence_data:
            for den_data in absence_data["Absences"]:
                den_info = {
                    "datum": den_data.get("Date", "").split("T")[0] if den_data.get("Date") else None,
                    "nevyreseno": den_data.get("Unsolved", 0),
                    "ok": den_data.get("Ok", 0),
                    "zmeskano": den_data.get("Missed", 0),
                    "pozdni_prichod": den_data.get("Late", 0),
                    "brzy_odchod": den_data.get("Soon", 0),
                    "skolni_akce": den_data.get("School", 0),
                    "distancni_vyuka": den_data.get("DistanceTeaching", 0),
                    "celkem_hodin": (den_data.get("Unsolved", 0) + den_data.get("Ok", 0) + 
                                   den_data.get("Missed", 0) + den_data.get("Late", 0) + 
                                   den_data.get("Soon", 0) + den_data.get("School", 0) + 
                                   den_data.get("DistanceTeaching", 0))
                }
                
                # Kontrola zda má den nějaké absence
                if den_info["celkem_hodin"] > 0:
                    formatted_absence["absence_podle_dni"].append(den_info)
                    formatted_absence["souhrn"]["dny_s_absenci"] += 1
                    
                    # Přičtení k celkovým statistikám
                    formatted_absence["souhrn"]["celkove_statistiky"]["nevyreseno"] += den_info["nevyreseno"]
                    formatted_absence["souhrn"]["celkove_statistiky"]["ok"] += den_info["ok"]
                    formatted_absence["souhrn"]["celkove_statistiky"]["zmeskano"] += den_info["zmeskano"]
                    formatted_absence["souhrn"]["celkove_statistiky"]["pozdni_prichod"] += den_info["pozdni_prichod"]
                    formatted_absence["souhrn"]["celkove_statistiky"]["brzy_odchod"] += den_info["brzy_odchod"]
                    formatted_absence["souhrn"]["celkove_statistiky"]["skolni_akce"] += den_info["skolni_akce"]
                    formatted_absence["souhrn"]["celkove_statistiky"]["distancni_vyuka"] += den_info["distancni_vyuka"]
                
                formatted_absence["souhrn"]["celkem_dni"] += 1
        
        # Zpracování absencí podle předmětů
        if "AbsencesPerSubject" in absence_data:
            for predmet_data in absence_data["AbsencesPerSubject"]:
                predmet_info = {
                    "nazev_predmetu": predmet_data.get("SubjectName", ""),
                    "pocet_hodin_celkem": predmet_data.get("LessonsCount", 0),
                    "zakladni_absence": predmet_data.get("Base", 0),
                    "pozdni_prichod": predmet_data.get("Late", 0),
                    "brzy_odchod": predmet_data.get("Soon", 0),
                    "skolni_akce": predmet_data.get("School", 0),
                    "distancni_vyuka": predmet_data.get("DistanceTeaching", 0)
                }
                
                # Výpočet procenta absence
                if predmet_info["pocet_hodin_celkem"] > 0:
                    celkem_absenci = (predmet_info["zakladni_absence"] + 
                                    predmet_info["pozdni_prichod"] + 
                                    predmet_info["brzy_odchod"])
                    predmet_info["procento_absence"] = round(
                        (celkem_absenci / predmet_info["pocet_hodin_celkem"]) * 100, 2
                    )
                    predmet_info["nad_prahem"] = predmet_info["procento_absence"] > (formatted_absence["prah_procent"] * 100)
                else:
                    predmet_info["procento_absence"] = 0
                    predmet_info["nad_prahem"] = False
                
                formatted_absence["absence_podle_predmetu"].append(predmet_info)
        
        # Seřazení předmětů podle procenta absence (sestupně)
        formatted_absence["absence_podle_predmetu"].sort(
            key=lambda x: x["procento_absence"], reverse=True
        )
        
        # Seřazení dní podle data (nejnovější první)
        formatted_absence["absence_podle_dni"].sort(
            key=lambda x: x["datum"] if x["datum"] else "", reverse=True
        )
        
        return formatted_absence
        
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
        
        # Vytvoření lookup tabulek - používáme konzistentní pojmenování
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
                    "name": teacher.get("Name"),
                    # Debug info pro diagnostiku
                    "raw_teacher": teacher
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
                "raw_data_sample": str(rozvrh_data)[:500] if rozvrh_data else "No data",
                "teachers_sample": list(teachers_lookup.values())[:3]  # Debug: ukázka učitelů
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
                                "atom_keys": list(atom.keys()),
                                "teacher_lookup_result": teachers_lookup.get(teacher_id, {})
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
                        # OPRAVENO: Používáme konzistentně plné jméno učitele, pokud není k dispozici, použijeme zkratku
                        ucitel = teacher_info.get("name") or teacher_info.get("abbrev")
                        
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
                            "ucitel_zkratka": teacher_info.get("abbrev"),
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


@mcp.tool()
async def znamky() -> Dict[str, Any]:
    """
    Získá všechny známky studenta organizované podle předmětů.
    
    Returns:
        Dict obsahující předměty s jejich známkami, průměry a dalšími informacemi
    """
    try:
        endpoint = "/api/3/marks"
        marks_data = await api_request(endpoint)
        
        # Zpracování dat o známkách
        formatted_marks = {
            "typ": "znamky",  
            "predmety": []
        }
        
        if "Subjects" in marks_data:
            for subject in marks_data["Subjects"]:
                subject_info = {
                    "predmet": {
                        "id": subject.get("Subject", {}).get("Id"),
                        "nazev": subject.get("Subject", {}).get("Name"),
                        "zkratka": subject.get("Subject", {}).get("Abbrev")
                    },
                    "prumer": (subject.get("AverageText") or "").strip(),
                    "docasna_znamka": (subject.get("TemporaryMark") or "").strip(),
                    "poznamka_k_predmetu": (subject.get("SubjectNote") or "").strip(),
                    "poznamka_k_docasne_znamce": (subject.get("TemporaryMarkNote") or "").strip(),
                    "pouze_body": subject.get("PointsOnly", False),
                    "predikce_povozena": subject.get("MarkPredictionEnabled", False),
                    "znamky": []
                }
                
                # Zpracování jednotlivých známek
                if "Marks" in subject:
                    for mark in subject["Marks"]:
                        mark_info = {
                            "id": mark.get("Id"),
                            "datum_znamky": mark.get("MarkDate", "").split("T")[0] if mark.get("MarkDate") else None,
                            "datum_editace": mark.get("EditDate", "").split("T")[0] if mark.get("EditDate") else None,
                            "nazev": (mark.get("Caption") or "").strip(),
                            "tema": (mark.get("Theme") or "").strip(),
                            "znamka_text": (mark.get("MarkText") or "").strip(),
                            "ucitel_id": mark.get("TeacherId"),
                            "typ": mark.get("Type"),
                            "typ_poznamka": (mark.get("TypeNote") or "").strip(),
                            "vaha": mark.get("Weight"),
                            "predmet_id": mark.get("SubjectId"),
                            "je_nova": mark.get("IsNew", False),
                            "je_bodova": mark.get("IsPoints", False),
                            "vypocitana_znamka": (mark.get("CalculatedMarkText") or "").strip(),
                            "poradi_ve_tride": mark.get("ClassRankText"),
                            "body_text": (mark.get("PointsText") or "").strip(),
                            "max_bodu": mark.get("MaxPoints", 0)
                        }
                        
                        # Přidání informací o bodování pokud je známka bodová
                        if mark_info["je_bodova"] and mark_info["max_bodu"] > 0:
                            try:
                                body_ziskane = float(mark_info["znamka_text"])
                                mark_info["procento"] = round((body_ziskane / mark_info["max_bodu"]) * 100, 2)
                            except (ValueError, ZeroDivisionError):
                                mark_info["procento"] = None
                        
                        subject_info["znamky"].append(mark_info)
                
                # Seřazení známek podle data (nejnovější první)
                subject_info["znamky"].sort(
                    key=lambda x: x["datum_znamky"] if x["datum_znamky"] else "", 
                    reverse=True
                )
                
                formatted_marks["predmety"].append(subject_info)
        
        # Seřazení předmětů podle názvu
        formatted_marks["predmety"].sort(key=lambda x: x["predmet"]["nazev"] or "")
        
        # Přidání souhrnu
        formatted_marks["souhrn"] = {
            "celkem_predmetu": len(formatted_marks["predmety"]),
            "celkem_znamek": sum(len(p["znamky"]) for p in formatted_marks["predmety"]),
            "nove_znamky": sum(len([z for z in p["znamky"] if z["je_nova"]]) for p in formatted_marks["predmety"]),
            "predmety_s_docasnou_znamkou": len([p for p in formatted_marks["predmety"] if p["docasna_znamka"]])
        }
        
        return formatted_marks
        
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
