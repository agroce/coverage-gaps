import csv
import datetime
import scipy
import scipy.stats

MAX_K = 100
MIN_DAYS = 0
MIN_COMMITS = 8

allProjects = set([])
allFiles = set([])

commitNumbers = {}
whichProjects = {}
projectChanges = {}
allTimes = {}
with open('coverage.csv', 'r') as projfile:
    projReader = csv.reader(projfile)
    for row in projReader:
        if row[0] != 'repo':
            allProjects.add(row[0])
            whichProjects[row[1]] = row[0]
            if row[0] not in projectChanges:
                projectChanges[row[0]] = [row[1]]
            else:
                projectChanges[row[0]].append(row[1])
        allTimes[row[1]] = row[4]

with open('coverage_jacoco.csv', 'r') as projfile:
    projReader = csv.reader(projfile)
    for row in projReader:
        if row[0] != 'date':
            allProjects.add(row[1])
            whichProjects[row[2]] = row[1]
            if row[1] not in projectChanges:
                projectChanges[row[1]] = [row[2]]
            else:
                projectChanges[row[1]].append(row[2])
        allTimes[row[2]] = row[5]

for p in projectChanges:
    psorted = sorted(projectChanges[p], key=lambda x:allTimes[x])
    index = 0
    for c in psorted:
        commitNumbers[c] = index
        index += 1
        
missingProject = 0
missingTime = 0
tried = 0
rejected = 0

targetProjects = {}
allChanges = {}

def days(duration):
    return ((duration/60.0)/60.0)/24.0

with open ('flapping_coveralls.csv') as flapfile:
    flapReader = csv.reader(flapfile)
    for row in flapReader:
        [commit, file, line, covered] = row
        allFiles.add(file)
        target = file + ":" + line
        commitOk = True
        tried += 1
        if commit not in whichProjects:
            missingProject += 1
            commitOk = False
            #print "MISSING FROM shaOrders.csv:", commit
        if commit not in allTimes:
            commitOk = False
            #print "MISSING FROM ShaAndTime.csv:", commit
            missingTime += 1
        if not commitOk:
            rejected += 1
            continue
        targetProjects[target] = whichProjects[commit]
        if target in allChanges:
            allChanges[target].append((commit, covered))
        else:
            allChanges[target] = [(commit, covered)]

with open ('flapping_jacoco.csv') as flapfile:
    flapReader = csv.reader(flapfile)
    for row in flapReader:
        [commit, file, line, covered] = row
        allFiles.add(file)
        target = file + ":" + line
        commitOk = True
        tried += 1
        if commit not in whichProjects:
            missingProject += 1
            commitOk = False
            #print "MISSING FROM shaOrders.csv:", commit
        if commit not in allTimes:
            commitOk = False
            #print "MISSING FROM ShaAndTime.csv:", commit
            missingTime += 1
        if not commitOk:
            rejected += 1
            continue
        targetProjects[target] = whichProjects[commit]
        if target in allChanges:
            allChanges[target].append((commit, covered))
        else:
            allChanges[target] = [(commit, covered)]

#print "MISSING PROJECT:", missingProject
#print "MISSING TIME:", missingTime
print "TOTAL REJECTED COMMITS:", rejected, "OUT OF", tried

for target in allChanges.keys():
    changes = allChanges[target]
    sortChanges = sorted(changes, key=lambda x:int(allTimes[x[0]]))
    allChanges[target] = sortChanges

# filter out any target with a switch with duration less than MIN_DAYS in size as possibly "flaky-covered"
newAllChanges = {}
nondetCount = 0

print len(allProjects), "TOTAL PROJECTS"
print len(allFiles), "TOTAL FILES"
print len(allChanges), "COVERAGE TARGETS TO ANALYZE"

for target in allChanges.keys():
    if len(allChanges[target]) == 1:
        newAllChanges[target] = allChanges[target]
    else:
        sequence = allChanges[target][1:]
        lastTime = int(allTimes[allChanges[target][0][0]])
        lastCommit = commitNumbers[allChanges[target][0][0]]
        nondeterminism = False
        for change in sequence:
            newTime = int(allTimes[change[0]])
            newCommit = commitNumbers[change[0]]
            duration = days(newTime-lastTime)
            if duration < MIN_DAYS:
                nondeterminism = True
                nondetCount += 1
                break
            if (newCommit-lastCommit) < MIN_COMMITS:
                nondeterminism = True
                nondetCount += 1
                break
            lastTime = newTime
            lastCommit = newCommit
        if not nondeterminism:
            newAllChanges[target] = allChanges[target]

print "FILTERED OUT", nondetCount, "COVERAGE TARGETS AS POSSIBLY NONDETERMINISTIC"

allChanges = newAllChanges
    
coveragePermanentlyDropped = {}
coverageLostK = {}
for k in range(1, MAX_K):
    coverageLostK[k] = {}
for target in allChanges:
    if allChanges[target][-1][1] == '0':
        coveragePermanentlyDropped[target] = allChanges[target]
        continue
    for k in range(1, MAX_K):
        pattern = []
        for j in range(0, k):
            pattern.extend(['0','1'])
        if map(lambda x:x[1], allChanges[target]) == pattern:
            coverageLostK[k][target] = (allChanges[target])
            break
        pattern = [1]
        for j in range(0, k):
            pattern.extend(['0','1'])
        if map(lambda x:x[1], allChanges[target]) == pattern:
            coverageLostK[k][target] = (allChanges[target])
            break        
        

print "COVERAGE PERMANENTLY DROPPED:", len(coveragePermanentlyDropped)
for k in range(1, MAX_K):
    if len(coverageLostK[k]) > 0:
        print "COVERAGE LOST", k, "TIMES:", len(coverageLostK[k])

filesWithChanges = set([])
projectsWithChanges = set([])
lostOnceSorted = sorted(coverageLostK[1].keys(), key=lambda x: int(allTimes[coverageLostK[1][x][1][0]]) - int(allTimes[coverageLostK[1][x][0][0]]))
howLong = []
howLongC = []
with open("k1." + str(MIN_COMMITS) + "." + str(MIN_DAYS) + ".days.1ok.csv", 'w') as f:
    f.write("target,project,days,#commits,commit1,commit2\n")
    for target in lostOnceSorted:
        duration = int(allTimes[coverageLostK[1][target][1][0]]) - int(allTimes[coverageLostK[1][target][0][0]])
        ncommits = commitNumbers[coverageLostK[1][target][1][0]] - commitNumbers[coverageLostK[1][target][0][0]]
        #print target, "GAP DAYS:", days(duration), "PROJECT:", targetProjects[target], "FROM", coverageLostOnce[target][0][0], "TO", coverageLostOnce[target][1][0]
        f.write(target + "," + targetProjects[target] + "," + str(days(duration)) + "," + str(ncommits) + "," +
                    coverageLostK[1][target][0][0] + "," + coverageLostK[1][target][1][0] + "\n")
        projectsWithChanges.add(targetProjects[target])
        filesWithChanges.add(target.split(":")[0])
        howLong.append(duration)
        howLongC.append(ncommits)

print len(filesWithChanges), "FILES HAVE SINGLE GAPS LASTING MORE THAN", MIN_DAYS ,"DAYS AND", MIN_COMMITS, "COMMITS:"
print filesWithChanges
print len(projectsWithChanges), "PROJECTS HAVE SINGLE GAPS LASTING MORE THAN", MIN_DAYS, "DAYS AND", MIN_COMMITS, "COMMITS:"
print projectsWithChanges

print len(howLong), "ONE-TIME COVERAGE GAPS LASTING MORE THAN", MIN_DAYS, "DAYS"
print "MINIMUM GAP:", days(min(howLong)), "DAYS"
print "MAXIMUM GAP:", days(max(howLong)), "DAYS"
print "MEAN GAP:", days(scipy.mean(howLong)), "DAYS"
print "MEDIAN GAP:", days(scipy.median(howLong)), "DAYS"

print len(howLongC), "ONE-TIME COVERAGE GAPS LASTING MORE THAN", MIN_COMMITS, "COMMITS"
print "MINIMUM GAP:", min(howLongC), "COMMITS"
print "MAXIMUM GAP:", max(howLongC), "COMMITS"
print "MEAN GAP:", scipy.mean(howLongC), "COMMITS"
print "MEDIAN GAP:", scipy.median(howLongC), "COMMITS"

if False and len(coverageLostK[2]) > 0:

    filesWithChanges = set([])
    projectsWithChanges = set([])
    lostOnceSorted = sorted(coverageLostK[2].keys(), key=lambda x: int(allTimes[coverageLostK[2][x][-1][0]]) - int(allTimes[coverageLostK[2][x][0][0]]))
    howLong = []
    howLongEach = []
    with open("k2." + str(MIN_DAYS) + ".days.1ok.csv", 'w') as f:
        f.write("target,project,days,commit1,commit2,commit3,commit4\n")
        for target in lostOnceSorted:
            duration = int(allTimes[coverageLostK[2][target][-1][0]]) - int(allTimes[coverageLostK[2][target][0][0]])
            #print target, "GAP DAYS:", days(duration), "PROJECT:", targetProjects[target], "FROM", coverageLostOnce[target][0][0], "TO", coverageLostOnce[target][1][0]
            f.write(target + "," + targetProjects[target] + "," + str(days(duration)) + "," +
                        coverageLostK[2][target][0][0] + "," + coverageLostK[2][target][1][0] + "," +
                        coverageLostK[2][target][2][0] + "," + coverageLostK[2][target][3][0] +"\n")
            projectsWithChanges.add(targetProjects[target])
            filesWithChanges.add(target.split(":")[0])
            howLong.append(duration)
            duration1 = int(allTimes[coverageLostK[2][target][1][0]]) - int(allTimes[coverageLostK[2][target][0][0]])
            duration2 = int(allTimes[coverageLostK[2][target][3][0]]) - int(allTimes[coverageLostK[2][target][2][0]])
            howLongEach.append(duration1)
            howLongEach.append(duration2)        

    print len(filesWithChanges), "FILES HAVE TWO GAPS LASTING MORE THAN", MIN_DAYS ,"DAYS:"
    print filesWithChanges
    print len(projectsWithChanges), "PROJECTS HAVE TWO GAPS LASTING MORE THAN", MIN_DAYS, "DAYS:"
    print projectsWithChanges

    print len(howLong), "TWO-TIME COVERAGE GAPS LASTING MORE THAN", MIN_DAYS, "DAYS"
    print "MINIMUM TOTAL PERIOD:", days(min(howLong)), "DAYS"
    print "MAXIMUM TOTAL PERIOD:", days(max(howLong)), "DAYS"
    print "MEAN TOTAL PERIOD:", days(scipy.mean(howLong)), "DAYS"
    print "MEDIAN TOTAL PERIOD:", days(scipy.median(howLong)), "DAYS"
    print "MINIMUM GAP:", days(min(howLongEach)), "DAYS"
    print "MAXIMUM GAP:", days(max(howLongEach)), "DAYS"
    print "MEAN GAP:", days(scipy.mean(howLongEach)), "DAYS"
    print "MEDIAN GAP:", days(scipy.median(howLongEach)), "DAYS"
