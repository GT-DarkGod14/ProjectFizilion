# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.d (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module containing commands related to android"""

import asyncio
import json
import math
import os
import re
import time
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup
from requests import get

from userbot import CMD_HELP, TEMP_DOWNLOAD_DIRECTORY, trgg
from userbot.events import register
from userbot.utils import chrome, human_to_bytes, humanbytes, md5, time_formatter

GITHUB = "https://github.com"


@register(outgoing=True, pattern="^\.magisk$".format(trg=trgg))
async def magisk(request):
    magisk_dict = {
        "Stable": "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/stable.json",
        "Beta": "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/beta.json",
        "Canary": "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/canary.json",
    }
    releases = "Latest Magisk Releases:\n"
    for name, release_url in magisk_dict.items():
        data = get(release_url).json()
        releases += (
            f'{name}: [APK v{data["magisk"]["version"]}]({data["magisk"]["link"]}) | '
            f'[Changelog]({data["magisk"]["note"]})\n'
        )
    await request.edit(releases)


@register(outgoing=True, pattern=r"^\.device(?: |$)(\S*)".format(trg=trgg))
async def device_info(request):
    """ get android device basic info from its codename """
    textx = await request.get_reply_message()
    codename = request.pattern_match.group(1)
    if codename:
        pass
    elif textx:
        codename = textx.text
    else:
        await request.edit("`Usage: .device <codename> / <model>`")
        return
    data = json.loads(
        get(
            "https://raw.githubusercontent.com/androidtrackers/"
            "certified-android-devices/master/by_device.json"
        ).text
    )
    results = data.get(codename)
    if results:
        reply = f"**Search results for {codename}**:\n\n"
        for item in results:
            reply += (
                f"**Brand**: {item['brand']}\n"
                f"**Name**: {item['name']}\n"
                f"**Model**: {item['model']}\n\n"
            )
    else:
        reply = f"`Couldn't find info about {codename}!`\n"
    await request.edit(reply)


@register(outgoing=True, pattern=r"^\.codename(?: |)([\S]*)(?: |)([\s\S]*)".format(trg=trgg))
async def codename_info(request):
    """ search for android codename """
    textx = await request.get_reply_message()
    brand = request.pattern_match.group(1).lower()
    device = request.pattern_match.group(2).lower()

    if brand and device:
        pass
    elif textx:
        brand = textx.text.split(" ")[0]
        device = " ".join(textx.text.split(" ")[1:])
    else:
        await request.edit("`Usage: .codename <brand> <device>`")
        return

    data = json.loads(
        get(
            "https://raw.githubusercontent.com/androidtrackers/"
            "certified-android-devices/master/by_brand.json"
        ).text
    )
    devices_lower = {k.lower(): v for k, v in data.items()}  # Lower brand names in JSON
    devices = devices_lower.get(brand)
    results = [
        i
        for i in devices
        if i["name"].lower() == device.lower() or i["model"].lower() == device.lower()
    ]
    if results:
        reply = f"**Search results for {brand} {device}**:\n\n"
        if len(results) > 8:
            results = results[:8]
        for item in results:
            reply += (
                f"**Device**: {item['device']}\n"
                f"**Name**: {item['name']}\n"
                f"**Model**: {item['model']}\n\n"
            )
    else:
        reply = f"`Couldn't find {device} codename!`\n"
    await request.edit(reply)


@register(outgoing=True, pattern="^\.pixeldl(?: |$)(.*)".format(trg=trgg))
async def download_api(dl):
    await dl.edit("`Collecting information...`")
    URL = dl.pattern_match.group(1)
    URL_MSG = await dl.get_reply_message()
    if URL:
        pass
    elif URL_MSG:
        URL = URL_MSG.text
    else:
        await dl.edit("`Empty information...`")
        return
    if not re.findall(r"\bhttps?://download.*pixelexperience.*\.org\S+", URL):
        await dl.edit("`Invalid information...`")
        return
    driver = await chrome()
    await dl.edit("`Getting information...`")
    driver.get(URL)
    error = driver.find_elements_by_class_name("swal2-content")
    if len(error) > 0:
        if error[0].text == "File Not Found.":
            await dl.edit(f"`FileNotFoundError`: {URL} is not found.")
            return
    datas = driver.find_elements_by_class_name("download__meta")
    """ - enumerate data to make sure we download the matched version - """
    md5_origin = None
    i = None
    for index, value in enumerate(datas):
        for data in value.text.split("\n"):
            if data.startswith("MD5"):
                md5_origin = data.split(":")[1].strip()
                i = index
                break
        if md5_origin is not None and i is not None:
            break
    if md5_origin is None and i is None:
        await dl.edit("`There is no match version available...`")
    if URL.endswith("/"):
        file_name = URL.split("/")[-2]
    else:
        file_name = URL.split("/")[-1]
    file_path = TEMP_DOWNLOAD_DIRECTORY + file_name
    download = driver.find_elements_by_class_name("download__btn")[i]
    download.click()
    await dl.edit("`Starting download...`")
    file_size = human_to_bytes(download.text.split(None, 3)[-1].strip("()"))
    display_message = None
    complete = False
    start = time.time()
    while complete is False:
        if os.path.isfile(file_path + ".crdownload"):
            try:
                downloaded = os.stat(file_path + ".crdownload").st_size
                status = "Downloading"
            except OSError:  # Rare case
                await asyncio.sleep(1)
                continue
        elif os.path.isfile(file_path):
            downloaded = os.stat(file_path).st_size
            file_size = downloaded
            status = "Checking"
        else:
            await asyncio.sleep(0.3)
            continue
        diff = time.time() - start
        percentage = downloaded / file_size * 100
        speed = round(downloaded / diff, 2)
        eta = round((file_size - downloaded) / speed)
        prog_str = "`{0}` | [{1}{2}] `{3}%`".format(
            status,
            "".join(["█" for i in range(math.floor(percentage / 10))]),
            "".join(["░" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2),
        )
        current_message = (
            "`[DOWNLOAD]`\n\n"
            f"`{file_name}`\n"
            f"`Status`\n{prog_str}\n"
            f"`{humanbytes(downloaded)} of {humanbytes(file_size)}"
            f" @ {humanbytes(speed)}`\n"
            f"`ETA` -> {time_formatter(eta)}"
        )
        if (
            round(diff % 15.00) == 0
            and display_message != current_message
            or (downloaded == file_size)
        ):
            await dl.edit(current_message)
            display_message = current_message
        if downloaded == file_size:
            if not os.path.isfile(file_path):  # Rare case
                await asyncio.sleep(1)
                continue
            MD5 = await md5(file_path)
            if md5_origin == MD5:
                complete = True
            else:
                await dl.edit("`Download corrupt...`")
                os.remove(file_path)
                driver.quit()
                return
    await dl.respond(f"`{file_name}`\n\n" f"Successfully downloaded to `{file_path}`.")
    await dl.delete()
    driver.quit()
    return




@register(outgoing=True, pattern=r"^\.twrp(?: |$)(\S*)".format(trg=trgg))
async def twrp(request):
    """ get android device twrp """
    textx = await request.get_reply_message()
    device = request.pattern_match.group(1)
    if device:
        pass
    elif textx:
        device = textx.text.split(" ")[0]
    else:
        await request.edit("`Usage: .twrp <codename>`")
        return
    url = get(f"https://dl.twrp.me/{device}/")
    if url.status_code == 404:
        reply = f"`Couldn't find twrp downloads for {device}!`\n"
        await request.edit(reply)
        return
    page = BeautifulSoup(url.content, "lxml")
    download = page.find("table").find("tr").find("a")
    dl_link = f"https://dl.twrp.me{download['href']}"
    dl_file = download.text
    size = page.find("span", {"class": "filesize"}).text
    date = page.find("em").text.strip()
    reply = (
        f"**Latest TWRP for {device}:**\n"
        f"[{dl_file}]({dl_link}) - __{size}__\n"
        f"**Updated:** __{date}__\n"
    )
    await request.edit(reply)

GSM_SEARCH_HOSTS = ("https://m.gsmarena.com", "https://www.gsmarena.com")
GSM_PAGE_HOSTS = ("https://www.gsmarena.com", "https://m.gsmarena.com")

gsm_headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_GSM_PHONE_SLUG = re.compile(r"^[^/]+-\d+\.php$")
_GSM_NOT_PHONE = re.compile(
    r"-(?:phones|reviews?|pictures|news|videos|related|compare|opinions)-", re.I
)


class GSMArenaBlocked(Exception):
    pass


def _gsm_is_blocked(response):
    if response.status_code in (403, 429, 503):
        return True
    head = response.text[:4000].lower()
    return "turnstile" in head or "one quick check before you continue" in head


def _gsm_get(session, path, hosts, params=None):
    blocked = False
    last_error = None
    for host in hosts:
        try:
            resp = session.get(
                host + path, params=params, headers=gsm_headers, timeout=15
            )
        except requests.RequestException as e:
            last_error = e
            continue
        if _gsm_is_blocked(resp):
            blocked = True
            continue
        if resp.status_code == 200:
            return resp
        last_error = RuntimeError(f"HTTP {resp.status_code} from {host}")
    if blocked:
        raise GSMArenaBlocked()
    raise last_error or RuntimeError("GSMArena request failed")


def _gsm_norm(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _gsm_tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _gsm_extract_candidates(soup):
    containers = [
        soup.select_one("div.makers"),
        soup.select_one("div#review-body"),
        soup.select_one("div.section-body"),
        soup,
    ]
    for container in containers:
        if container is None:
            continue
        found, seen = [], set()
        for a in container.find_all("a", href=True):
            slug = urlparse(a["href"]).path.rsplit("/", 1)[-1]
            if not _GSM_PHONE_SLUG.match(slug) or _GSM_NOT_PHONE.search(slug):
                continue
            if slug in seen:
                continue
            seen.add(slug)
            name = a.get_text(" ", strip=True)
            if not name and a.find("img"):
                name = (a.find("img").get("title") or a.find("img").get("alt") or "").strip()
            if not name:
                name = re.sub(r"-\d+\.php$", "", slug).replace("_", " ")
            found.append((name, slug))
        if found:
            return found
    return []


def _gsm_pick_best(query, candidates):
    q_norm = _gsm_norm(query)
    q_tokens = _gsm_tokens(query)
    if not q_tokens:
        return None
    best, best_score = None, 0.0
    for idx, (name, slug) in enumerate(candidates):
        n_norm = _gsm_norm(name)
        n_tokens = set(_gsm_tokens(name))
        ratio = sum(1 for t in q_tokens if t in n_tokens) / len(q_tokens)
        if ratio < 0.5:
            continue
        score = ratio
        if n_norm == q_norm:
            score += 2
        elif n_norm.endswith(q_norm):
            score += 1.5
        elif q_norm in n_norm:
            score += 0.5
        extra = len(n_tokens) - len(q_tokens)
        if extra > 0:
            score -= 0.05 * extra
        score -= idx * 0.001
        if score > best_score:
            best, best_score = (name, slug), score
    return best


def _gsm_parse_specs(soup):
    all_specs = {}
    for table in soup.find_all("table"):
        current = None
        last_name = None
        for row in table.find_all("tr"):
            th = row.find("th")
            if th:
                current = th.get_text(" ", strip=True)
                all_specs.setdefault(current, {})
                last_name = None
            ttl = row.find("td", class_="ttl")
            nfo = row.find("td", class_="nfo")
            if not (ttl and nfo and current):
                continue
            name = ttl.get_text(" ", strip=True)
            value = re.sub(r"\s+", " ", nfo.get_text(" ", strip=True)).strip()
            if not value or value == "-":
                continue
            if name:
                all_specs[current][name] = value
                last_name = name
            elif last_name:
                all_specs[current][last_name] += "; " + value
    return {k: v for k, v in all_specs.items() if v}


def _gsm_format(phone_name, all_specs, phone_url):
    reply = f"**📱 {phone_name}**\n\n"
    important_order = [
        "Network", "Launch", "Body", "Display", "Platform",
        "Memory", "Main Camera", "Selfie Camera", "Battery",
    ]

    def block(cat_name, specs_dict, limit):
        out = f"**{cat_name.upper()}**\n"
        for spec_name, spec_value in list(specs_dict.items())[:limit]:
            if len(spec_value) > 100:
                spec_value = spec_value[:100] + "..."
            out += f"• **{spec_name}**: {spec_value}\n"
        return out + "\n"

    shown = set()
    for wanted in important_order:
        for cat_name, specs_dict in all_specs.items():
            if cat_name not in shown and wanted.lower() in cat_name.lower():
                reply += block(cat_name, specs_dict, 5)
                shown.add(cat_name)
                break
    for cat_name, specs_dict in all_specs.items():
        if cat_name not in shown and len(reply) < 3500:
            reply += block(cat_name, specs_dict, 3)

    reply += f"[Full specs on GSMArena]({phone_url})"
    if len(reply) > 4000:
        reply = reply[:3900] + f"\n\n`...truncated`\n[Full specs on GSMArena]({phone_url})"
    return reply


@register(outgoing=True, pattern=r"^\.specs(?: |)([\s\S]*)".format(trg=trgg))
async def devices_specifications(request):
    textx = await request.get_reply_message()
    device_query = request.pattern_match.group(1).strip()
    if device_query:
        pass
    elif textx:
        device_query = textx.text.strip()
    else:
        await request.edit("`Usage: .specs <phone name>`\n`Example: .specs iPhone 15 Pro`")
        return
    if not device_query:
        await request.edit("`Please provide a phone name`\n`Example: .specs Samsung Galaxy S24`")
        return
    await request.edit(f"`🔍 Searching specifications for {device_query}...`")
    manual_url = f"https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName={quote(device_query)}"
    try:
        session = requests.Session()
        resp = _gsm_get(
            session, "/results.php3", GSM_SEARCH_HOSTS,
            params={"sQuickSearch": "yes", "sName": device_query},
        )
        candidates = _gsm_extract_candidates(BeautifulSoup(resp.content, "html.parser"))
        best = _gsm_pick_best(device_query, candidates)
        if not best:
            await request.edit(f"`⚠ No results found for {device_query}`")
            return
        phone_name, slug = best
        phone_resp = _gsm_get(session, "/" + slug, GSM_PAGE_HOSTS)
        phone_soup = BeautifulSoup(phone_resp.content, "html.parser")
        phone_url = f"https://www.gsmarena.com/{slug}"
        name_elem = phone_soup.find("h1", class_="specs-phone-name-title") or phone_soup.find("h1")
        if name_elem and name_elem.get_text(strip=True):
            phone_name = name_elem.get_text(" ", strip=True)
        all_specs = _gsm_parse_specs(phone_soup)
        if all_specs:
            await request.edit(
                _gsm_format(phone_name, all_specs, phone_url), link_preview=False
            )
        else:
            await request.edit(
                f"**📱 {phone_name}**\n\n`⚠ Could not extract specifications`\n"
                f"`Try checking manually:` {phone_url}"
            )
    except GSMArenaBlocked:
        await request.edit(
            "`⚠ GSMArena is blocking automated requests right now (anti-bot check).`\n"
            f"`Try again in a few minutes or search manually:` {manual_url}"
        )
    except requests.exceptions.Timeout:
        await request.edit(f"`⏱️ Timeout searching for {device_query}`")
    except Exception:
        await request.edit(f"`⚠ Error processing {device_query}`")


@register(outgoing=True, pattern=r"^\.ofox(?: |$)(\S*)")
async def ofox(request):
    """ get android device ofox """
    textx = await request.get_reply_message()
    device = request.pattern_match.group(1)
    if device:
        pass
    elif textx:
        device = textx.text.split(" ")[0]
    else:
        await request.edit("`Usage: .ofox <codename>`")
        return
    url = get(f"https://api.orangefox.download/v3/devices/get?codename={device}")
    if url.status_code == 404:
        await request.edit(f"`Couldn't find OrangeFox Recovery for {device}!`\n")
        return
    info = json.loads(url.text)
    if 'url' in info:
        ed = (
            f"**Latest OFOX Recovery for {info['full_name']}:**\n"
            f"[{device}]({info['url']})\n"
            f"Maintainer: {info['maintainer']['name']}"
        )
        await request.edit(ed)
    else:
        await request.edit("Mmmm... Some issue occured")


CMD_HELP.update(
    {
        "android": ".magisk\
\nGet latest Magisk releases\
\n\n.device <codename>\
\nUsage: Get info about android device codename or model.\
\n\n.codename <brand> <device>\
\nUsage: Search for android device codename.\
\n\n.pixeldl **<download.pixelexperience.org>**\
\nUsage: Download pixel experience ROM into your userbot server.\
\n\n.specs <brand> <device>\
\nUsage: Get device specifications info.\
\n\n.twrp <codename>\
\nUsage: Get latest twrp download for android device.\
\n\n.ofox <codename>\
\nUsage: Get latest ofox recovery download for android device."
    }
)
