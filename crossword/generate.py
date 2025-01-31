import sys
from queue import SimpleQueue

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for i in self.domains.keys():
            lst = []
            for word in self.domains[i]:
                if (len(word) != i.length):
                    lst.append(word)
            for word in lst:
                self.domains[i].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        overlap = self.crossword.overlaps[x, y]
        if (overlap is not None):
            for word1 in self.domains[x]:
                for word2 in self.domains[y]:
                    if (word1[overlap[0]] != word2[overlap[1]]):
                        self.domains.remove(word1)
                        revised = True
                        break
        return revised


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        q = SimpleQueue()
        if (arcs is not None):
            for i in arcs:
                q.put(i)
        else:
            for i in self.crossword.variables:
                for j in self.crossword.variables:
                    if (i != j):
                        q.put((i, j))
        while not q.empty:
            arc = q.get()
            if (self.revise(arc[0], arc[1])):
                if (len(self.domains[arc[0]]) == 0):
                    return False
                for i in self.crossword.neighbors(arc[0]):
                    if (i != arc[1]):
                        q.put((i, arc[0]))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for i in self.crossword.variables:
            if (not assignment.get(i, 0)):
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        for i in assignment.keys():
            if (i.length != len(assignment[i])):
                return False
        for i in assignment.keys():
            for j in assignment.keys():
                if (i != j):
                    overlap = self.crossword.overlaps[i, j]
                    if (overlap is None):
                        continue
                    if (assignment[i][overlap[0]] != assignment[j][overlap[1]]):
                        return False
                    if (assignment[i] == assignment[j]):
                        return False
        return True

    def rules_out_values(self, var, word, neighbors, assignment):
        count = 0
        for i in neighbors:
            if not assignment.get(i, 0):
                for j in self.domains[i]:
                    if (j == word):
                        count += 1
                        continue
                    overlap = self.crossword.overlaps[i, var]
                    if (overlap is None):
                        continue
                    if (word[overlap[1]] != j[overlap[0]]):
                        count += 1
        return count

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        rules_out = []
        for i in self.domains[var]:
            rules_out.append((i, self.rules_out_values(var, i, self.crossword.neighbors(var), assignment)))
        return [x[0] for x in sorted(rules_out, key = lambda i: i[1])]


    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned_variables = []
        for i in self.crossword.variables:
            if (not assignment.get(i, 0)):
                unassigned_variables.append((i, len(self.crossword.neighbors(i)), len(self.domains[i])))
        unassigned_variables.sort(key = lambda x: x[2])
        unassigned = []
        for i in unassigned_variables:
            if (i[2] != unassigned_variables[0][2]):
                break
            unassigned.append(i)
        return max(unassigned, key = lambda x: x[1])[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if (self.assignment_complete(assignment)):
            return assignment
        start = self.select_unassigned_variable(assignment)
        for i in self.order_domain_values(start, assignment):
            assignment[start] = i
            if (self.consistent(assignment)):
                result = self.backtrack(assignment)
                if (result != None):
                    return result
            del assignment[start]
        return None
                


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
