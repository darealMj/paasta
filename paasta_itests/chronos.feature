Feature: paasta_tools can interact with chronos

  Scenario: Trivial chronos jobs can be deployed
    Given a working paasta cluster
    When we create a trivial chronos job
    And the trivial chronos job appears in the job list
    Then we should be able to see it when we list jobs

# vim: set ts=2 sw=2
