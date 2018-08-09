import csv
import datetime
import scipy

whichProjects = {}
projectChanges = {}
allTimes = {}
with open('coverage.csv', 'r') as projfile:
    projReader = csv.reader(projfile)
    for row in projReader:
        if row[0] != 'repo':
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
            whichProjects[row[2]] = row[1]
            if row[1] not in projectChanges:
                projectChanges[row[1]] = [row[2]]
            else:
                projectChanges[row[1]].append(row[2])
        allTimes[row[2]] = row[5]

if False:
    allTimes = {}
    with open('ShaAndTime.csv', 'r') as timefile:
        timeReader = csv.reader(timefile)
        for row in timeReader:
            if row[0] != 'SHA':
                allTimes[row[0]] = row[1]

missingProject = 0
missingTime = 0
tried = 0
rejected = 0

targetProjects = {}
allChanges = {}

with open ('flapping_coveralls.csv') as flapfile:
    flapReader = csv.reader(flapfile)
    for row in flapReader:
        [commit, file, line, covered] = row
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

coveragePermanentlyDropped = {}
coverageLostOnce = {}
for target in allChanges:
    if len(allChanges[target]) == 1:
        if allChanges[target][0][1] == '0':
            coveragePermanentlyDropped[target] = allChanges[target]
    if len(allChanges[target]) == 2:    
        if allChanges[target][0][1] == '0':
            if allChanges[target][1][1] != '1':
                continue
            coverageLostOnce[target] = (allChanges[target])

def days(duration):
    return ((duration/60.0)/60.0)/24.0

filesWithChanges = set([])
projectsWithChanges = set([])

lostOnceSorted = sorted(coverageLostOnce.keys(), key=lambda x: int(allTimes[coverageLostOnce[x][1][0]]) - int(allTimes[coverageLostOnce[x][0][0]]))

howLong = []
for target in lostOnceSorted:
    duration = int(allTimes[coverageLostOnce[target][1][0]]) - int(allTimes[coverageLostOnce[target][0][0]])
    if days(duration) > 7:
        print target, "GAP DAYS:", days(duration), "PROJECT:", targetProjects[target], "FROM", coverageLostOnce[target][0][0], "TO", coverageLostOnce[target][1][0]
        projectsWithChanges.add(targetProjects[target])
        file = target.split(":")[0]
        if file not in filesWithChanges:
            filesWithChanges.add(file)
        howLong.append(duration)


print len(filesWithChanges), "FILES HAVE GAPS LASTING MORE THAN 7 DAYS:"
print filesWithChanges
print len(projectsWithChanges), "PROJECTS HAVE GAPS LASTING MORE THAN 7 DAYS:"
print projectsWithChanges

print len(howLong), "ONE-TIME COVERAGE GAPS LASTING MORE THAN 7 DAYS"
print "MINIMUM GAP:", days(min(howLong)), "DAYS"
print "MAXIMUM GAP:", days(max(howLong)), "DAYS"
print "MEAN GAP:", days(scipy.mean(howLong)), "DAYS"
print "MEADIAN GAP:", days(scipy.median(howLong)), "DAYS"
