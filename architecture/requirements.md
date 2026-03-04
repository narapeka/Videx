# High Level Requirement
I want to build a tool which can help me to manager and organize my media files. This tool should be able to monitor new incoming files, recoganize them by LLM and TMDB, and organize them into right folders with better file names, and then with an option to generate strm files and inform emby server to scan new strm files.

# Background
1. I have a cloud storage named 115 Cloud, where I store media files there, including movie and tv shows.
2. I use CloudDrive2 to mount 115 Cloud to my local disk.
3. I usally get new media files by 115 share links and save new media files into 115 folder like 'My recieved'
4. For playing, I generate strm files and then use emby to scan strm files for building media libraries.

# Use Case Example

## Folder structure
```
/root/
    /my recieved/
        Test movie1.web-dl.2160p.AAC.mp4
        Test movie2.REMUX.1080p.DTS.mkv
        Test movie3.UHD.HEVC.2160p.TrueHD7.1.iso
        /Test tv show1/
            episode1.mkv
            episode2.mkv
        /Test tv show2/
            S01
                test-episode1.S01E01.mkv
                test-episode2.S01E02.mkv
            S02
                1.mp4
                2.mp4
        /Test movie4/
            Test movie4.UHD.disc1.iso
            Test movie4.UHD.disc2.iso
```

## Expectations
The app should be able to correclty distinguish movie and tv shows, and then rely on the foler name/file name, it can recoganize the media using LLM model and TMDB api. Based on tmdb result, it can reorganize the media files into a well-structured folder like:

```
/root/
    /my organized/
        /Web-DL Movies/
            /Test movie1 (2009) {tmdb-123456}/
                Test movie1.mp4
        /REMUX Movies/
            /Test Movie2 (2022) {tmdb-234555}/
                Test movie2.mkv
        /ISO Movies/
            /Test movie3 (2025) {tmdb-777777}/
                Test movie3.iso
            /Test movie4 (2026) {tmdb-988888}/
                Test movie4.disc1.iso
                Test movie4.disc2.iso
        /Chinese TV Shows/
            /Test tv show1 (2002) {tmdb-222222}/
                /Season 1/
                    Test tv show1 - S01E01 - episode title.mkv
                    Test tv show1 - S01E02 - episode title.mkv
        /Europe TV Shows/
            /Test tv show2 (2005) {tmdb-5555555}/
                /Season 1/
                    Test tv show2 - S01E01 - episode title.mkv
                    Test tv show2 - S01E02 - episode title.mkv
                /Season 2/
                    Test tv show2 - S02E01 - episode title.mp4
                    Test tv show2 - S02E02 - episode title.mp4
```

# Detail Requirements

## Typical Process Flow

watch -> recoganize media -> rename and organize -> transfer to library -> generate strm files -> inform emby server

1. The app start and watch on the changes on local mounted folders (based on configuration)
2. When new changes arrived (by polling observer), the app read the folder structure and then call LLM model and tmdb api to recoganize medias
3. For high confidence matchs, the app then renaming the media files (by configured nameing rules) and organize them into proper folders
4. Based on user action or predefiend scheduler, the app then transfer organized files into formal media library folders and generate strm files accordingly
5. The app then call emby api to notify the refresh for updated libary paths (optional, as the emby server can also monitor strm file changes)

## Configuration

CloudDrive2 grpc configuration (user, password, address etc. grpc is used because it is faster then operating local mounted file systems)
LLM configration (api key, model, base_url, batch size etc.)
TMDB configuration (api key, proxy, rate limit etc.)
Monitor configuration ( watch folders -> target folders, polling intervals etc.)
Naming rules (patterns like {movie_name} {year} {tmdb-{tmdbid}})
Category rules (based on tmdb info and file name keywords, organize files into different folders like web-dl, remux, chinese tv shows etc.)
Transfer rules (basically a map list between organized folders to library folders, with conditions like overwrite, generate A-Z subfolders etc.)
strm generation rules (rules of strm file content - path to local mount, or with some additional prefix, suffix etc.)
emby configuration (emby address, port, user and password or webhook api key)


## Technical Considerations

Modulized approached for extensiblity and easy enhancement
    watch monitoring
    file operation
    llm client
    tmdb client
    movie recoganizer
    tv show recoganizer
    renaming and category service
    transfer service
    strm generation
    emby client
Run report: well formatted for review