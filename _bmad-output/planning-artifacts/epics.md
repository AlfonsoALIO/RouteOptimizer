---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
inputDocuments:
  - README.md
  - core/main.py
  - core/__init__.py
  - core/optimization.py
  - core_search/run.py
  - core_search/state.py
  - core_search/search.py
  - lean_ui/fleet_ui/forms.py
  - lean_ui/fleet_ui/views.py
---

# RouteOptimizer - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for RouteOptimizer, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

Requirements were extracted from the dynamic-routing review of the current tree. No PRD, architecture spine, or UX design contract exists in this repository. The confirmed inventory below is the requirements source.

## Requirements Inventory

### Functional Requirements

FR1: One scenario describes locations, arcs with travel time, demand by source and destination, truck capacities, horizon, and fleet size, and both the A* dispatcher and the batch MILP consume it.

FR2: That scenario can be built from haul rows, keeping the loader as the source and the destination, distance, and haul time as the arc.

FR3: The fleet form can edit the scenario, including the graph, demands, and truck capacities, in addition to segment count and truck count.

FR4: Each search step offers alternative assignments of a truck class onto feasible arcs, plus idle and return-to-garage, instead of one greedy bundle.

FR5: A movement is costed by the travel time of the arc taken.

FR6: Dispatch can replan a short horizon from the current truck positions when a shovel stops, a queue fills, or demand changes.

FR7: Two fleet states with the same trucks and coverage at different times are different states, including an in-transit arc.

FR8: The batch optimizer is one flow over arcs and segments, with conservation, queue capacity, fleet size, and demand that can change by segment.

FR9: Tonnage demand and shift length from Parameters are inputs to that model.

FR10: When A* finds a cheaper copy of a queued state, the queue stores the cost with the node and heap order stays valid.

FR11: LinearProblem takes its locations from the travel-time map as real endpoints, and the model can use those pairs.

FR12: The scenario has a documented, versioned file format that a mine can produce from its own data without the SQL Server schema.

FR13: A mine can install the package and run the dispatcher and the shift plan on a scenario file from the command line.

FR14: A solve can be given a time limit, and stops at that limit with a reported status instead of running without bound.

FR15: The package is distributed as a pip package and a Docker image, under a stated license, with a Hugging Face repository that links to both and carries sample scenarios.

### NonFunctional Requirements

NFR1: Assignments are grouped by capacity class so identical trucks are not fully permuted.

NFR2: The current toy mine remains a runnable scenario so the UI works without SQL Server.

NFR3: Database credentials stay in .env. Machine filters are scenario inputs, not the only query path.

NFR4: Running the package on a mine's data makes no network calls, so the data stays on the mine's machines.

NFR5: The package installs without a commercial solver license.

### Additional Requirements

- FleetState identity must include the segment and any in-transit arc. Today the hash is coverage plus resident trucks, so a later arrival collapses into an earlier node.
- AStar.solve must replace a queued node with the (cost, node) tuple and restore heap order. Today the replacement stores the node alone.
- LinearProblem.locations must be the actual endpoints from the travel-time map. Today it is assigned the unbound method arc_times.keys, and the model never reads it.
- Per-arc subproblems in core/main.py are replaced by the single network model. They are not solved beside it.
- Parameters (tonnage_demand, shift_length) is already constructed in core/main.py and must be passed into the model instead of the literals for demand, capacity context, horizon, and fleet size.
- calculate_route_times must group by source and destination. Today it groups by destination only.
- The SQL haul query must not be limited to the four hardcoded machine ids as the only data path.

### UX Design Requirements

No UX design contract was in scope. The fleet form change is covered by FR3.

### FR Coverage Map

FR1: Epic 2 — One scenario feeds both solvers
FR2: Epic 2 — Haul rows become source-to-destination arcs
FR3: Epic 2 — The form edits the mine, not only two counts
FR4: Epic 3 — Search offers alternate arc assignments
FR5: Epic 3 — Cost is arc travel time
FR6: Epic 4 — Replan from current truck positions
FR7: Epic 1 and Epic 3 — Segment distinguishes two arrivals; the in-transit arc joins that identity once travel time exists
FR8: Epic 5 — One flow model over arcs and segments
FR9: Epic 5 — Tonnage demand and shift length enter the model
FR10: Epic 1 — A cheaper queued state keeps its cost
FR11: Epic 1 — Locations are the travel-time endpoints

NFR1: Epic 3 — Assignments group by capacity class
NFR2: Epic 2 — The toy mine remains a runnable fixture
NFR3: Epic 2 — Credentials stay in .env and machine filters are inputs

FR12: Epic 6 — Documented scenario file format
FR13: Epic 6 — Install and run from the command line
FR14: Epic 6 — Time-limited solves
FR15: Epic 6 — pip package, Docker image, license, and Hugging Face repository

NFR4: Epic 6 — No network calls on a mine's data
NFR5: Epic 6 — No commercial solver license required

## Epic List

### Epic 1: Keep the better route
Running today's UI or today's batch job keeps the assignment the solver preferred. Endpoints are real locations. The same trucks at two different times stay two states.

Done when a worse node already on the open set is replaced by the cheaper one and that node is the one returned, and when travel-time endpoints are inputs the formulation reads. The segment distinguishes two arrivals of the same trucks and coverage. An in-transit arc joins that identity when travel time exists. This epic does not wait on a new scenario or a new model.
**FRs covered:** FR10, FR7, FR11

### Epic 2: Run both solvers on a mine you specify
A planner loads haul history or edits the mine, and both the dispatcher and the batch job read that same scenario. The toy mine remains one fixture. The current search behavior stays as it is.

Done when one schema carries resident capacity, directed arcs with travel time, demand by pair, trucks, horizon, and fleet size, and both entry points load it. A missing field fails the load. The toy mine is the one named fixture that may be synthetic. Demand and truck capacity are in tons, shift length is in hours, and arc travel time is in minutes.
**FRs covered:** FR1, FR2, FR3
**NFRs covered:** NFR2, NFR3

### Epic 3: Send trucks on different arcs
A dispatch considers more than one assignment, and a trip is costed by that arc's travel time. Identical trucks are grouped by capacity. This epic does not include replan.

Done when the objective is travel time, identical capacities stay grouped, and the toy scenario returns inside the interactive request.
**FRs covered:** FR4, FR5
**NFRs covered:** NFR1

### Epic 4: Replan from where the trucks are
A dispatcher revises a short horizon from current truck positions when a shovel stops, a queue fills, or demand changes.

Done when the window goal is the best feasible dispatch over the next k segments from the current positions. The garage requirement applies when the horizon is the rest of the shift.
**FRs covered:** FR6

### Epic 5: Produce one shift plan across the mine
An analyst solves one flow over arcs and segments from the shared scenario, with tonnage demand and shift length as inputs.

Done when a fixture with a known feasible flow solves and conserves trucks, an infeasible scenario returns a reported status, and the units are the ones defined on the Epic 2 scenario: tons, shift length in hours, and arc travel time in minutes.
**FRs covered:** FR8, FR9

### Epic 6: Download and run it at your mine
A mining company installs the package, converts its own data to the scenario file format, and runs the dispatcher and the shift plan on its own machines. The Hugging Face repository is where a company finds it.

Done when a clean machine can install the pip package or the Docker image, run both solvers on the sample scenarios with no database and no network calls, stop a long solve at a time limit, and read the license and the file format from the Hugging Face repository.
**FRs covered:** FR12, FR13, FR14, FR15
**NFRs covered:** NFR4, NFR5

Epic 1 stands alone. Epic 2 stands alone. Epic 3 depends on Epic 1 and Epic 2. Epic 4 depends on Epic 3. Epic 5 depends on Epic 1 and Epic 2 only. Epic 6 depends on Epic 1, Epic 2, and Epic 5. It ships whatever dispatcher exists at the time and does not wait on Epic 3 or Epic 4.

## Epic 1: Keep the better route

Running today's UI or today's batch job keeps the assignment the solver preferred. Endpoints are real locations. The same trucks at two different times stay two states.

Done when a worse node already on the open set is replaced by the cheaper one and that node is the one returned, and when travel-time endpoints are inputs the formulation reads. The segment distinguishes two arrivals of the same trucks and coverage. An in-transit arc joins that identity when travel time exists. This epic does not wait on a new scenario or a new model.

**FRs covered:** FR10, FR7, FR11

### Story 1.1: Keep the cheaper assignment that is already waiting

As a dispatcher,
I want a cheaper way to reach a fleet state that is already waiting to be expanded,
So that the plan I see is the better route the search actually found.

**Acceptance Criteria:**

**Given** a fleet state already on the open set at cost C
**When** the search generates the same state at cost C′ < C
**Then** the open-set entry becomes the cheaper node paired with C′
**And** the heap order is valid after the replacement
**And** the solution returned is that cheaper node when it is the best goal

**Given** a fleet state already on the open set at cost C
**When** the search generates the same state at cost C′ ≥ C
**Then** the waiting entry stays the original node at cost C

**Given** the current `AStar.solve` control flow, where a child already waiting is not updated and the decrease-key path runs only for an explored state and stores the node without its cost
**When** the cheaper waiting state is generated
**Then** that waiting entry is the one replaced
**And** the stored value is the `(cost, node)` pair

**Tasks:**

1. Add a search fixture with two paths to one state, the worse path queued first.
2. Update `AStar.solve` so a cheaper unexplored copy replaces the waiting entry as `(cost, node)` and the heap is restored.
3. Leave an equal or higher cost on the open set unchanged.
4. Assert the returned goal is the cheaper node.

### Story 1.2: Tell two arrival times of the same fleet apart

As a dispatcher,
I want the same trucks and the same tons moved at a later segment to count as a different state,
So that a later arrival is still available to the search.

**Acceptance Criteria:**

**Given** two fleet states with the same covered demand and the same resident trucks
**When** their segments differ
**Then** the states are not equal
**And** their hashes differ
**And** A* treats them as different nodes

**Given** two fleet states with the same covered demand, the same resident trucks, and the same segment
**When** they are compared
**Then** they are equal

**Given** state equality
**When** it is evaluated
**Then** it compares covered demand, resident assignments, and segment
**And** an equal hash is not treated as proof that the states are the same

**Tasks:**

1. Add `segment` to the identity that `FleetState` hashes and compares.
2. Compare those fields in `__eq__` instead of comparing hashes.
3. Test that the same trucks and coverage at two segments are distinct search nodes.
4. Test that the same segment still counts as one state.

### Story 1.3: Read arc endpoints inside the linear formulation

As an analyst,
I want the batch model to build its variables from the arc endpoints in the travel-time map,
So that the plan names real locations.

**Acceptance Criteria:**

**Given** a travel-time map and an arc whose destination is a key in that map
**When** a `LinearProblem` is constructed
**Then** `locations` is the arc's endpoints
**And** `locations` is not the unbound `keys` method
**And** the segment count is taken from that destination's travel time

**Given** that problem
**When** the formulation is built
**Then** the assignment variables and the fleet-size constraint iterate `locations`
**And** the model finishes building

**Given** an arc whose destination is absent from the travel-time map
**When** a `LinearProblem` is constructed
**Then** construction fails with an error that names the missing destination

**Tasks:**

1. Set `locations` from the arc endpoints and look up the destination in the travel-time map.
2. Build the assignment variables and the fleet-size constraint from `locations`.
3. Pass that constraint an affine expression of those variables so the model can build.
4. Test a known destination, and test that a missing destination fails at construction.

## Epic 2: Run both solvers on a mine you specify

A planner loads haul history or edits the mine, and both the dispatcher and the batch job read that same scenario. The toy mine remains one fixture. The current search behavior stays as it is.

Done when one schema carries resident capacity, directed arcs with travel time, demand by pair, trucks, horizon, and fleet size, and both entry points load it. A missing field fails the load. The toy mine is the one named fixture that may be synthetic. Demand and truck capacity are in tons, shift length is in hours, and arc travel time is in minutes.

**FRs covered:** FR1, FR2, FR3
**NFRs covered:** NFR2, NFR3

### Story 2.1: Reject an incomplete mine

As a planner,
I want a mine described in one scenario, with tons for demand, hours for the shift, and minutes for arc travel time,
So that an incomplete mine is rejected instead of being filled in with hidden literals.

**Acceptance Criteria:**

**Given** locations with resident capacity, directed arcs with travel time in minutes, demand in tons by source and destination, trucks with capacity in tons, a shift length in hours, and a fleet size
**When** the scenario is loaded
**Then** the loaded scenario keeps those fields and those units

**Given** a payload missing any of those fields
**When** the scenario is loaded
**Then** loading fails
**And** the error names the missing field

**Given** an arc or a demand whose endpoint is not one of the locations
**When** the scenario is loaded
**Then** loading fails
**And** the error names the unknown location

**Tasks:**

1. Add a scenario type with those fields: tons, shift length in hours, and arc travel time in minutes.
2. Reject a missing required field by name.
3. Reject an arc or a demand that names a location outside the scenario.
4. Test one valid payload and one payload with a missing field.

### Story 2.2: Run the dispatcher on the toy-mine fixture

As a planner,
I want the fleet screen to simulate the current toy mine without a database,
So that I can still run a dispatch before any haul history is loaded.

**Acceptance Criteria:**

**Given** the named toy-mine fixture
**When** it is loaded
**Then** it is a valid scenario
**And** it contains shovels S1 and S2, loaders L1 and L2, waste dump W, crusher C, and the garage
**And** each of those six working locations has resident capacity 2
**And** the directed connections match the mine in `core_search/run.py`
**And** the demands are S1→C 8000 t, S2→C 1200 t, L1→C 4000 t, S1→W 1600 t, S2→W 2000 t, and L1→W 1000 t
**And** every arc has a travel time in minutes
**And** truck capacity is 100 t

**Given** the fleet screen supplies a segment count and a truck count
**When** the dispatcher runs on that fixture
**Then** the horizon and the number of trucks come from those two values
**And** the search uses the fixture's locations, arcs, demands, and truck capacity
**And** the assignment rules stay the current ones
**And** travel time is carried on the arcs and is not yet the search objective
**And** the run finishes without SQL Server

**Given** the dispatcher
**When** it builds the mine
**Then** the only synthetic mine is this named fixture

**Tasks:**

1. Build the toy mine as a named scenario fixture, including a travel time in minutes on every arc.
2. Start the dispatcher from that fixture, using the requested segment count and truck count.
3. Remove the inline mine from `core_search/run.py`.
4. Test that a dispatch still runs with no database and that the demands and locations match the fixture.

### Story 2.3: Run the batch job on the same scenario

As an analyst,
I want the batch job to solve a scenario the dispatcher can already load,
So that both tools plan the same mine.

**Acceptance Criteria:**

**Given** a valid scenario, including the toy-mine fixture
**When** the batch job runs on it
**Then** it builds one subproblem for each directed arc
**And** the fleet size comes from the scenario
**And** each arc's travel time in minutes comes from the scenario
**And** each subproblem's segment count is the scenario shift length converted to minutes, divided by that arc's travel time, rounded up
**And** the literals 29, 10 hours, and 2 shifts are not used
**And** the run finishes without SQL Server

**Given** the dispatcher from Story 2.2
**When** the batch job runs
**Then** the fleet screen still takes its segment count and truck count from the form

**Given** the current per-arc model
**When** a subproblem is solved
**Then** the tonnage constraint stays the current one
**And** the result is still persisted for the job

**Tasks:**

1. Run the batch entry point from a scenario object.
2. Compute each arc's segment count from the shift length in minutes divided by that arc's travel time in minutes.
3. Take the fleet size from the scenario and remove the literals 29, 10, and 2.
4. Test the batch job on the toy-mine fixture with no database, and test that the dispatcher form values are unchanged.

### Story 2.4: Edit the mine from the fleet form

As a planner,
I want to change the mine's locations, arcs, demands, and truck capacity from the fleet screen,
So that the dispatch I run is the mine I described.

**Acceptance Criteria:**

**Given** the fleet screen is opened
**When** the page is shown
**Then** the form is filled from the toy-mine fixture
**And** it includes locations with resident capacity, directed arcs with travel time in minutes, demands in tons, truck capacity in tons, segment count, and truck count
**And** the route and demand tables are rendered from that scenario

**Given** a valid edit to the graph, a demand, or the truck capacity
**When** the planner submits the form
**Then** the dispatcher runs on that edited scenario
**And** the output corresponds to the submitted locations, arcs, and demands

**Given** a submission with a missing required field or an unknown location
**When** the planner submits the form
**Then** the screen shows an error that names the problem
**And** no simulation runs

**Tasks:**

1. Replace the two-field form with the scenario fields, initially filled from the toy-mine fixture.
2. Render the route and demand tables from the scenario instead of the fixed HTML.
3. On a valid submit, load the scenario and run the dispatcher.
4. On an invalid submit, show the named error and skip the run.

### Story 2.5: Load the mine from haul rows

As an analyst,
I want haul history to become a scenario whose arcs run from the loader to the destination,
So that the solvers plan the mine the trucks actually ran.

**Acceptance Criteria:**

**Given** haul rows with a loader (`CargCo`), a destination, a distance, and a haul time
**When** the rows are loaded with a caller-supplied demand, truck definition, resident capacity, shift length, and fleet size
**Then** each loader and each destination is a location
**And** each loader-destination pair is one directed arc
**And** the arc keeps the distance and the mean haul time of that pair, expressed in minutes
**And** the result is a valid scenario

**Given** a machine filter supplied by the caller
**When** the rows are read
**Then** only those loaders are included
**And** database credentials are read from the environment

**Given** no machine filter
**When** the rows are read
**Then** the load is not restricted to `C243`, `R418`, `R422`, and `R417`

**Given** a row missing a loader, destination, or haul time, or a caller input missing demand, trucks, resident capacity, shift length, or fleet size
**When** the scenario is loaded
**Then** loading fails
**And** the error names the missing field

**Tasks:**

1. Accept the loader list as an input and read credentials from the environment.
2. Map `CargCo` to the arc source and keep destination, distance, and haul time.
3. Average haul time by loader and destination, and store it in minutes.
4. Build a scenario with the caller-supplied demand, trucks, resident capacity, shift length, and fleet size.
5. Test a filtered load, an unfiltered load, and a row missing the loader.

## Epic 3: Send trucks on different arcs

A dispatch considers more than one assignment, and a trip is costed by that arc's travel time. Identical trucks are grouped by capacity. This epic does not include replan.

Done when the objective is travel time, identical capacities stay grouped, and the toy scenario returns inside the interactive request.

**FRs covered:** FR4, FR5
**NFRs covered:** NFR1

### Story 3.1: Choose among assignments of a truck class

As a dispatcher,
I want more than one legal way to send the trucks that are waiting at a location,
So that the search can pick a different arc when the first one is worse.

**Acceptance Criteria:**

**Given** trucks of one capacity at a source, and two feasible arcs with remaining demand and an open slot
**When** the actions for that state are generated
**Then** more than one assignment of that capacity class is returned
**And** an assignment can send the class onto either arc
**And** idling and returning to the garage remain choices

**Given** two trucks with the same capacity
**When** the assignments are generated
**Then** those trucks are not expanded as individually distinct permutations

**Given** the toy-mine fixture
**When** the fleet screen runs it
**Then** the screen receives a completed dispatch

**Tasks:**

1. Generate alternate slot assignments from `FleetState.possible_actions`, grouped by capacity class.
2. Keep idle and return-to-garage as actions.
3. Test two equal-capacity trucks and two open arcs, and test that equal trucks do not multiply the assignments.
4. Test that the toy-mine fixture returns a dispatch through the fleet screen.

### Story 3.2: Cost the dispatch by travel time

As a dispatcher,
I want the chosen plan to be the one that spends less time on the arcs,
So that a longer haul is not treated as equal to a shorter one.

**Acceptance Criteria:**

**Given** a movement along an arc
**When** its cost is added
**Then** the added cost is that arc's travel time in minutes

**Given** two completed dispatches that cover the same demand
**When** one has a smaller total travel time
**Then** the search returns that dispatch

**Given** the remaining-work estimate
**When** it is added to the ranking cost
**Then** the estimate is in minutes
**And** a trip count is not added to a time cost

**Given** the toy-mine fixture
**When** the fleet screen runs it
**Then** the reported objective is in minutes
**And** the screen receives a completed dispatch

**Tasks:**

1. Add each arc's travel time, in minutes, as the cost of taking that arc.
2. Express the remaining-work estimate in minutes.
3. Report the fleet-screen objective in minutes.
4. Test that the lower total travel time wins, and that the toy-mine fixture still returns.

### Story 3.3: Remember which arc a truck is on

As a dispatcher,
I want a truck that has not finished its haul to stay on that arc,
So that the search cannot send it somewhere else before it arrives.

**Acceptance Criteria:**

**Given** a scenario shift length in hours and a segment count
**When** one segment elapses
**Then** the clock advances by the shift length converted to minutes, divided by the segment count

**Given** a truck sent onto an arc whose travel time is longer than one segment
**When** one segment elapses
**Then** the truck is recorded in transit on that arc with the remaining minutes
**And** the next assignment does not include that truck

**Given** a truck whose remaining minutes fit in the next segment
**When** that segment elapses
**Then** the truck is resident at the destination

**Given** two states with the same covered demand, the same resident trucks, and the same segment
**When** their in-transit arcs or remaining minutes differ
**Then** the states are not equal
**And** A* treats them as different nodes

**Tasks:**

1. Advance the clock by the segment length in minutes.
2. Keep a truck on its arc until the remaining travel time reaches zero, and exclude it from assignment until then.
3. Include the in-transit arc and the remaining minutes in state equality.
4. Test a haul longer than one segment, the arrival on the following segment, and two states that differ only by the arc in transit.

## Epic 4: Replan from where the trucks are

A dispatcher revises a short horizon from current truck positions when a shovel stops, a queue fills, or demand changes.

Done when the window goal is the best feasible dispatch over the next k segments from the current positions. The garage requirement applies when the horizon is the rest of the shift.

**FRs covered:** FR6

### Story 4.1: Plan the next k segments from the current fleet

As a dispatcher,
I want a plan for the next k segments that starts from where the trucks are now,
So that I can revise the shift without sending everyone back to the garage first.

**Acceptance Criteria:**

**Given** trucks resident at locations and trucks in transit on arcs
**When** a horizon of k segments is solved
**Then** the search starts from those positions
**And** a truck in transit stays on its arc until its remaining minutes reach zero
**And** the returned plan covers the most remaining demand that k segments can cover
**And** among those plans it has the least travel time in minutes
**And** the trucks are not required to be in the garage

**Given** the horizon runs through the end of the shift
**When** the search finishes
**Then** every truck is in the garage
**And** the remaining demand is covered

**Given** k is zero, or the current segment is already the end of the shift
**When** a plan is requested
**Then** no new movements are produced

**Tasks:**

1. Start the search from a supplied fleet state, including trucks in transit.
2. Rank a k-segment window by demand covered, then by travel time in minutes.
3. Require the garage and full demand only when the window reaches the end of the shift.
4. Test a mid-shift start, a window that reaches the shift end, and a request with k equal to zero.

### Story 4.2: Replan when the mine changes

As a dispatcher,
I want a new plan when a shovel stops, a queue is full, or a demand changes,
So that trucks are not sent into a mine that no longer matches the shift.

**Acceptance Criteria:**

**Given** a current fleet, including trucks in transit, and a shovel whose resident capacity is set to zero
**When** the dispatcher replans
**Then** the next k segments are solved from those positions
**And** no new movement sends a truck to that shovel
**And** a truck already in transit is not reassigned

**Given** a destination whose resident trucks already equal its capacity
**When** the dispatcher replans
**Then** no new movement sends another truck to that destination

**Given** a change to a route's demand
**When** the dispatcher replans
**Then** the next k segments use the updated demand
**And** the search starts from the current positions

**Given** the fleet screen
**When** the planner submits one of these changes with the current fleet
**Then** the screen shows the revised plan

**Tasks:**

1. Accept the current fleet state and one mine change: a shovel closed, a full queue, or an edited demand.
2. Solve the next k segments from that state.
3. Leave in-transit trucks on their arcs, and refuse new assignments onto a closed shovel or a full queue.
4. Test each of the three changes from the fleet screen.

## Epic 5: Produce one shift plan across the mine

An analyst solves one flow over arcs and segments from the shared scenario, with tonnage demand and shift length as inputs.

Done when a fixture with a known feasible flow solves and conserves trucks, an infeasible scenario returns a reported status, and the units are the ones defined on the Epic 2 scenario: tons, shift length in hours, and arc travel time in minutes.

**FRs covered:** FR8, FR9

### Story 5.1: Solve one flow for the whole mine

As an analyst,
I want one model that moves trucks from arc to arc across the shift,
So that a truck that leaves a location is the same truck that arrives at the next.

**Acceptance Criteria:**

**Given** a scenario fixture with a known feasible assignment
**When** the batch job solves it
**Then** it builds one model for the whole scenario
**And** it does not solve a separate model for each arc
**And** at every location and segment, trucks present equal trucks that stayed, plus trucks that arrived, minus trucks that left
**And** trucks at a location do not exceed its resident capacity
**And** trucks in use in a segment do not exceed the fleet size
**And** the arc endpoints come from the scenario

**Given** a scenario with no feasible flow
**When** the batch job solves it
**Then** the result reports the infeasible status
**And** the job does not record that run as a success

**Tasks:**

1. Replace the per-arc loop with one flow model over arcs and segments.
2. Enforce conservation, resident capacity, and fleet size.
3. Test the known feasible fixture and check conservation at each location.
4. Test an infeasible scenario and assert the reported status.

### Story 5.2: Apply the shift's demand

As an analyst,
I want the shift length and the tons required in each segment to drive the flow,
So that the plan meets the demand for that shift instead of a placeholder.

**Acceptance Criteria:**

**Given** `Parameters` with a shift length in hours and a tonnage demand in tons
**When** the model is built
**Then** those values are read from `Parameters`
**And** a missing value fails the run and names the missing field
**And** the horizon is that shift length

**Given** a scenario segment count
**When** the horizon is divided
**Then** the model has that many segments
**And** each segment's length is the shift length converted to minutes, divided by the segment count

**Given** a demand in tons that differs by arc and by segment
**When** the model is solved
**Then** each segment is required to move that segment's tons
**And** the demand of 1 on every segment is not used
**And** truck capacity is the scenario's capacity in tons
**And** the literal capacity 100 is not used

**Given** a demand the fleet cannot cover within the shift
**When** the model is solved
**Then** the result reports the infeasible status

**Tasks:**

1. Pass `Parameters.shift_length` and `Parameters.tonnage_demand` into the model.
2. Require each arc and segment to move its own demand in tons.
3. Take truck capacity from the scenario and remove the literals `T = 1` and `C = 100`.
4. Test a demand that changes by segment, a missing parameter, and a demand the fleet cannot cover.

## Epic 6: Download and run it at your mine

A mining company installs the package, converts its own data to the scenario file format, and runs the dispatcher and the shift plan on its own machines. The Hugging Face repository is where a company finds it.

Done when a clean machine can install the pip package or the Docker image, run both solvers on the sample scenarios with no database and no network calls, stop a long solve at a time limit, and read the license and the file format from the Hugging Face repository.

**FRs covered:** FR12, FR13, FR14, FR15
**NFRs covered:** NFR4, NFR5

### Story 6.1: Publish under a stated license

As a mining company,
I want to know the terms under which I may run and change this software,
So that our legal team can approve using it.

**Acceptance Criteria:**

**Given** the repository
**When** it is opened
**Then** a `LICENSE` file states the license
**And** the README names that license
**And** the package metadata declares the same license

**Given** the work credited in the README to Alfonso Bonillas and alioit.com
**When** the license is chosen
**Then** the code owner has recorded that they hold the rights to release it

**Given** each runtime dependency
**When** its license is checked
**Then** it is compatible with the chosen license

**Tasks:**

1. Code owner chooses the license and confirms the rights with the original authors.
2. Add `LICENSE`, and name the license in the README.
3. Record each runtime dependency's license and confirm compatibility.

### Story 6.2: Describe a mine in a documented file

As a mining engineer,
I want a written file format for a scenario,
So that I can convert our fleet management data without our database matching the original SQL schema.

**Acceptance Criteria:**

**Given** the scenario fields from Story 2.1
**When** the file format is documented
**Then** each field has a name, a type, a unit, and whether it is required
**And** demand and truck capacity are in tons, shift length is in hours, and arc travel time is in minutes
**And** the file carries a format version

**Given** a scenario file in that format
**When** it is loaded
**Then** it produces the same scenario as the Story 2.1 loader
**And** a missing field, an unknown location, or an unsupported format version fails with an error that names the problem

**Given** the toy-mine fixture
**When** it is written in that format
**Then** it is published as a sample file
**And** a second sample, exported from haul history and anonymized, is published only after the data owner approves its release

**Tasks:**

1. Document the scenario file format, with units and a format version.
2. Load and validate scenario files through the Story 2.1 loader.
3. Write the toy mine as a sample file.
4. Prepare an anonymized sample from haul history, and publish it only with the data owner's approval.
5. Test a valid file, a missing field, and an unsupported version.

### Story 6.3: Install and run from the command line

As a mining engineer,
I want to install the package and run it on our scenario file,
So that we can plan with our own data on our own machines.

**Acceptance Criteria:**

**Given** a clean Python environment
**When** the package is installed with `pip`
**Then** it installs without a commercial solver license
**And** the command-line tool is available

**Given** a scenario file
**When** the dispatch command runs on it
**Then** it writes the dispatch as a file
**And** it exits with status 0

**Given** a scenario file
**When** the shift-plan command runs on it
**Then** it writes the plan and the solver status as a file
**And** an infeasible scenario exits with a nonzero status and reports infeasible

**Given** an invalid scenario file
**When** either command runs
**Then** it exits with a nonzero status and the error names the problem

**Given** either command running on a scenario file
**When** it runs to completion
**Then** it makes no network calls
**And** it does not require SQL Server

**Tasks:**

1. Add `pyproject.toml` with the package, its dependencies, and its license.
2. Add dispatch and shift-plan commands that read a scenario file and write the result as a file.
3. Return a nonzero exit status for an invalid scenario or an infeasible plan.
4. Test a clean install, both commands on the sample files, and a run with networking disabled.

### Story 6.4: Stop a long solve at a time limit

As a mining engineer,
I want to cap how long a solve may run,
So that a large fleet does not leave the tool running without an answer.

**Acceptance Criteria:**

**Given** a time limit in seconds
**When** the dispatcher reaches it before finding a dispatch
**Then** it stops
**And** it reports that the time limit was reached
**And** it does not report a dispatch as optimal

**Given** a time limit in seconds
**When** the shift plan reaches it
**Then** the solver stops
**And** it reports the solver status
**And** it marks any plan returned as not proven optimal

**Given** no time limit
**When** a solve runs
**Then** it behaves as it did before

**Tasks:**

1. Add a time-limit option to both commands.
2. Stop the A* search at the limit and report that status.
3. Pass the limit to the linear solver and report its status.
4. Test a scenario that exceeds a short limit for each solver.

### Story 6.5: Run it from a Docker image

As a mine's IT team,
I want a container image with the package and the solver,
So that we can run it without managing a Python installation.

**Acceptance Criteria:**

**Given** the published image
**When** it runs a command against a scenario file mounted from the host
**Then** it writes the result to the mounted folder
**And** it makes no network calls

**Given** the image
**When** it is built from a tagged release
**Then** the image version matches the package version

**Tasks:**

1. Add a Dockerfile that installs the package and its solver.
2. Run the command-line tool against a mounted scenario folder.
3. Tag the image with the package version.
4. Test both commands in the container with networking disabled.

### Story 6.6: Find it on Hugging Face

As a mining company,
I want a Hugging Face repository that explains the tool and links to it,
So that we can find it, judge it, and install it.

**Acceptance Criteria:**

**Given** the Hugging Face repository
**When** it is opened
**Then** its README states what the tool does, what it does not do, the license, and that it is an optimization solver with no trained weights
**And** it links to the pip package and the Docker image
**And** it links to the scenario file format
**And** it includes the sample scenario files from Story 6.2

**Given** a sample scenario from the repository
**When** it is run with the pip package or the Docker image
**Then** it returns a dispatch and a shift plan

**Tasks:**

1. Write the repository README with the scope, the limits, the license, and the install instructions.
2. Upload the sample scenarios and link to the file format.
3. Link the pip package and the Docker image.
4. Run each sample with both install methods.
